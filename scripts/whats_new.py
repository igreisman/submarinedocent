#!/usr/bin/env python3
"""Generate the weekly What's New entry from the week's commits.

Run every Friday at 02:00 Pacific by .github/workflows/whats-new.yml, and by
hand with --since/--until to rebuild or backfill a week.

Why it reads the git log rather than a hand-kept file: a changelog someone has
to remember to write is a changelog that stops. This one cannot fall behind,
because the commits are the record.

What it deliberately leaves out. A commit that touches no visitor-facing path
is not news to a visitor: the licence text, the contributing guide, CI, internal
notes and API plumbing all change without anything on the site changing. Only
commits touching web/ or a corpora/*.jsonl are listed. A revert and the commit
it reverts cancel out and both are dropped, because "we did X" followed by "we
undid X" describes a week in which X did not happen.

The counts are the part a visitor can actually use: how many answers, videos and
museum pages there are now, and how many there were last Friday.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, time, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:                                     # pragma: no cover
    ZoneInfo = None

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DEFAULT = os.path.join(REPO, "web", "whats-new.json")
ALL_DEFAULT = os.path.join(REPO, "web", "whats-new-all.json")

# The site's own clock. Fixed rather than "local" so the workflow running in UTC
# and a laptop in California agree on which week an entry belongs to.
SITE_TZ = "America/Los_Angeles"
CUTOFF_HOUR = 2

# Counted at both ends of the window and shown as "was -> now".
COUNTED = [
    ("corpora/dieselsubs_faq_corpus.jsonl", "Answers", lambda r: _answerable(r)),
    ("corpora/videos.jsonl", "Videos", None),
    ("corpora/museums.jsonl", "Museums listed", None),
    ("corpora/museum_pages.jsonl", "Museum pages", None),
]

# Path prefix -> the heading a visitor sees. First match wins, so order matters.
AREAS = [
    ("corpora/dieselsubs_faq_corpus.jsonl", "Answers"),
    ("corpora/dieselsubs_faq_categories.jsonl", "Answers"),
    ("corpora/videos.jsonl", "Videos"),
    ("corpora/museums.jsonl", "Museum pages"),
    ("corpora/museum_pages.jsonl", "Museum pages"),
    ("corpora/dieselsubs_glossary.jsonl", "Glossary"),
    ("corpora/eternal_patrol.jsonl", "Lost boats"),
    ("corpora/incidents.jsonl", "Lost boats"),
    ("corpora/", "Reference material"),
    ("web/museums.html", "Museum pages"),
    ("web/videos.html", "Videos"),
    ("web/video-search.html", "Videos"),
    ("web/video-card.js", "Videos"),
    ("web/faqs.html", "Answers"),
    ("web/askthedocent.html", "Ask the Docent"),
    ("web/glossary.html", "Glossary"),
    ("web/", "Pages and layout"),
]
# Housekeeping that moves bytes without changing what anyone reads: syncing the
# repository's seed copy of the corpus with what production already serves.
MAINTENANCE_SUBJECT = re.compile(r"^Refresh the (corpus )?seed( from production)?$", re.I)

# Under web/ but not news. The editors, the FAQ editor, the admin banner and the
# local test harness are pages no visitor loads. The two changelog data files are
# this script's own output: an entry announcing that last week's entry was
# written is noise, and it would appear every single week.
ADMIN_WEB = ("web/edit", "web/faq_editor.html", "web/admin-env-banner.js",
             "web/test.html", "web/whats-new.json", "web/whats-new-all.json")

# Whats-new: hide | show — an explicit answer in the commit message itself,
# which beats every path rule in both directions.
TRAILER = re.compile(r"^Whats-new:\s*(hide|show)\s*$", re.I | re.M)

OVERRIDES_FILE = os.path.join(REPO, "scripts", "whats_new_overrides.txt")


def load_overrides():
    """sha -> {"show"|"hide", area, reason}, for commits already pushed.

    Paths are a proxy, and a proxy is wrong in both directions: a corpora/
    change can be the repository catching up with production, and an
    api/main.py change can alter every answer on the site.
    """
    out = {}
    if not os.path.exists(OVERRIDES_FILE):
        return out
    with open(OVERRIDES_FILE, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 2)
            if len(parts) < 2 or parts[0] not in ("show", "hide"):
                continue
            verb, sha, rest = parts[0], parts[1], (parts[2] if len(parts) > 2 else "")
            if verb == "hide":
                out[sha] = {"verb": "hide", "area": "", "reason": rest or "excluded by hand"}
                continue
            # "show" carries the area first, then the reason.
            area, _, reason = rest.partition("  ")
            out[sha] = {"verb": "show", "area": area.strip(),
                        "reason": reason.strip() or "included by hand"}
    return out

AREA_ORDER = ["Answers", "Ask the Docent", "Videos", "Museum pages", "Glossary",
              "Lost boats", "Reference material", "Pages and layout"]


def _answerable(record):
    return str(record.get("chunk_id", "")).startswith(("faq_", "fix_"))


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args],
                          capture_output=True, text=True).stdout


def tz():
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(SITE_TZ)
    except Exception:
        return None


def default_window():
    """The week that just ended: previous Friday 02:00 to this Friday 02:00."""
    now = datetime.now(tz())
    cutoff = datetime.combine(now.date(), time(CUTOFF_HOUR), tzinfo=now.tzinfo)
    # Friday is weekday 4. Walk back to the most recent Friday 02:00 not ahead of us.
    days_since_friday = (now.weekday() - 4) % 7
    until = cutoff - timedelta(days=days_since_friday)
    if until > now:
        until -= timedelta(days=7)
    return until - timedelta(days=7), until


def counts_at(commit):
    out = {}
    for path, label, keep in COUNTED:
        blob = git("show", f"{commit}:{path}")
        if not blob.strip():
            continue
        n = 0
        for line in blob.splitlines():
            line = line.strip()
            if not line:
                continue
            if keep is None:
                n += 1
                continue
            try:
                if keep(json.loads(line)):
                    n += 1
            except Exception:
                continue
        out[label] = n
    return out


def area_for(paths):
    for path in paths:
        # corpora/ holds the content AND its own README. Only the .jsonl files
        # are what a visitor reads; documenting the corpus is not site news.
        if path.startswith("corpora/") and not path.endswith(".jsonl"):
            continue
        for prefix, area in AREAS:
            if path == prefix or path.startswith(prefix):
                return area
    return None


def collect(since, until):
    fmt = "%H%x1f%h%x1f%s%x1f%aI%x1f%P%x1f%b%x1e"
    raw = git("log", f"--since={since.isoformat()}", f"--until={until.isoformat()}",
              f"--pretty=format:{fmt}", "--date-order", "--no-merges")
    commits = []
    for record in raw.split("\x1e"):
        line = record.strip("\n")
        if not line.strip():
            continue
        full, short, subject, when, parents, body = line.split("\x1f")
        files = [f for f in git("show", "--name-only", "--pretty=format:", full).splitlines() if f.strip()]
        commits.append({"sha": short, "full": full, "subject": subject,
                        "date": when, "parents": parents.split(),
                        "body": body, "files": files})

    # A revert and its target cancel out. git revert writes the subject as
    # Revert "<original subject>", which is what this matches on.
    reverted = set()
    for c in commits:
        m = re.match(r'^Revert "(.+)"$', c["subject"])
        if m and any(o["subject"] == m.group(1) for o in commits):
            reverted.add(c["subject"])
            reverted.add(m.group(1))

    overrides = load_overrides()

    kept = []
    for c in commits:
        c["area"] = area_for(c["files"])
        trailer = TRAILER.search(c.get("body") or "")
        decision = trailer.group(1).lower() if trailer else ""
        override = overrides.get(c["sha"])
        if not decision and override:
            decision = override["verb"]
            if decision == "show" and override["area"]:
                c["area"] = override["area"]

        if decision == "show":
            c["public"], c["reason"] = True, ""
        elif decision == "hide":
            c["public"] = False
            c["reason"] = (override or {}).get("reason") or "the commit asked to be hidden"
        elif not c["parents"]:
            # The root commit lists the whole tree, which would file the entire
            # site as one week's news.
            c["public"], c["reason"] = False, "the repository's first commit"
        elif c["subject"] in reverted:
            c["public"], c["reason"] = False, "done and undone in the same week"
        elif MAINTENANCE_SUBJECT.match(c["subject"]):
            c["public"], c["reason"] = False, "brought the repository seed in line with production"
        elif all(any(f.startswith(a) for a in ADMIN_WEB) for f in c["files"]):
            c["public"], c["reason"] = False, "an editing screen, not a visitor page"
        elif c["area"] is None:
            c["public"], c["reason"] = False, "changed nothing a visitor loads"
        else:
            c["public"], c["reason"] = True, ""

        if c["public"]:
            kept.append(c)
    return commits, kept


def build_entry(since, until):
    all_commits, kept = collect(since, until)
    base = git("rev-list", "-1", f"--before={since.isoformat()}", "HEAD").strip()
    head = git("rev-parse", "HEAD").strip()

    groups = {}
    for c in kept:
        groups.setdefault(c["area"], []).append(
            {"sha": c["sha"], "summary": c["subject"]})
    ordered = [{"area": a, "changes": groups[a]}
               for a in AREA_ORDER if a in groups]
    ordered += [{"area": a, "changes": groups[a]}
                for a in sorted(groups) if a not in AREA_ORDER]

    before = counts_at(base) if base else {}
    after = counts_at(head)
    totals = [{"label": label, "was": before.get(label), "now": after[label]}
              for _p, label, _k in COUNTED if label in after]

    shared = {
        "week_ending": until.date().isoformat(),
        "from": since.date().isoformat(),
        "to": until.date().isoformat(),
        "generated": datetime.now(tz()).isoformat(timespec="seconds"),
        "commits_total": len(all_commits),
        "commits_listed": len(kept),
    }

    public = dict(shared, totals=totals, groups=ordered)

    # The admin changelog is the whole week with nothing dropped, each commit
    # carrying whether it reached the public page and why not. The point of
    # recording the reason is that a wrong call shows up as a sentence someone
    # can disagree with, rather than as an absence nobody notices.
    everything = dict(shared, commits=[{
        "sha": c["sha"],
        "summary": c["subject"],
        "date": c["date"],
        "area": c["area"] or "",
        "files": len(c["files"]),
        "public": c["public"],
        "reason": c["reason"],
    } for c in all_commits])

    return public, everything


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--all-out", default=ALL_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.since or args.until:
        if not (args.since and args.until):
            sys.exit("give both --since and --until, or neither")
        zone = tz()
        since = datetime.fromisoformat(args.since).replace(tzinfo=zone)
        until = datetime.fromisoformat(args.until).replace(tzinfo=zone)
    else:
        since, until = default_window()

    entry, everything = build_entry(since, until)
    print(f"window {since.isoformat()} .. {until.isoformat()}")
    print(f"  {entry['commits_listed']} of {entry['commits_total']} commits reach the public page")
    for g in entry["groups"]:
        print(f"    {g['area']}: {len(g['changes'])}")
    held = [c for c in everything["commits"] if not c["public"]]
    if held:
        print(f"  {len(held)} held back:")
        for c in held:
            print(f"    {c['sha']}  {c['reason']}")

    if args.dry_run:
        print(json.dumps(entry, indent=2)[:900])
        return 0

    # The admin log is written for every week, including a week in which nothing
    # visitor-facing happened: "we changed things you cannot see" is exactly what
    # it is for.
    _merge(args.all_out, everything)
    print(f"  wrote {args.all_out}")

    if entry["commits_listed"] == 0:
        print("  nothing a visitor can see this week; public page unchanged")
        return 0
    _merge(args.out, entry)
    print(f"  wrote {args.out}")
    return 0


def _merge(path, entry):
    """Insert an entry, replacing any existing one for the same week."""
    entries = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            entries = json.load(f).get("entries", [])
    entries = [e for e in entries if e.get("week_ending") != entry["week_ending"]]
    entries.insert(0, entry)
    entries.sort(key=lambda e: e["week_ending"], reverse=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"entries": entries}, f, indent=2, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
