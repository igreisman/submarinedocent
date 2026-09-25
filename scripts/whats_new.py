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
MAINTENANCE_SUBJECT = re.compile(r"^Refresh the (corpus )?seed\b", re.I)

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
    fmt = "%H%x1f%h%x1f%s%x1f%aI%x1f%P"
    raw = git("log", f"--since={since.isoformat()}", f"--until={until.isoformat()}",
              f"--pretty=format:{fmt}", "--date-order", "--no-merges")
    commits = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        full, short, subject, when, parents = line.split("\x1f")
        files = [f for f in git("show", "--name-only", "--pretty=format:", full).splitlines() if f.strip()]
        commits.append({"sha": short, "full": full, "subject": subject,
                        "date": when, "parents": parents.split(), "files": files})

    # A revert and its target cancel out. git revert writes the subject as
    # Revert "<original subject>", which is what this matches on.
    reverted = set()
    for c in commits:
        m = re.match(r'^Revert "(.+)"$', c["subject"])
        if m and any(o["subject"] == m.group(1) for o in commits):
            reverted.add(c["subject"])
            reverted.add(m.group(1))

    kept = []
    for c in commits:
        if c["subject"] in reverted:
            continue
        if not c["files"]:
            continue
        # The root commit lists the whole tree, which would file the entire site
        # as this week's news.
        if not c["parents"]:
            continue
        if MAINTENANCE_SUBJECT.match(c["subject"]):
            continue
        area = area_for(c["files"])
        if area is None:
            continue
        c["area"] = area
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

    return {
        "week_ending": until.date().isoformat(),
        "from": since.date().isoformat(),
        "to": until.date().isoformat(),
        "generated": datetime.now(tz()).isoformat(timespec="seconds"),
        "totals": totals,
        "groups": ordered,
        # Honest arithmetic: how many commits there were, and how many of them
        # changed nothing a visitor can see.
        "commits_total": len(all_commits),
        "commits_listed": len(kept),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--out", default=OUT_DEFAULT)
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

    entry = build_entry(since, until)
    print(f"window {since.isoformat()} .. {until.isoformat()}")
    print(f"  {entry['commits_listed']} of {entry['commits_total']} commits are visitor-facing")
    for g in entry["groups"]:
        print(f"  {g['area']}: {len(g['changes'])}")

    if entry["commits_listed"] == 0:
        print("  nothing visitor-facing this week; no entry written")
        return 0

    entries = []
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as f:
            entries = json.load(f).get("entries", [])
    # Rebuilding a week replaces it rather than adding a second copy.
    entries = [e for e in entries if e.get("week_ending") != entry["week_ending"]]
    entries.insert(0, entry)
    entries.sort(key=lambda e: e["week_ending"], reverse=True)

    if args.dry_run:
        print(json.dumps(entry, indent=2)[:1200])
        return 0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"entries": entries}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  wrote {args.out} ({len(entries)} entr{'y' if len(entries)==1 else 'ies'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
