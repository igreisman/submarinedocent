#!/usr/bin/env python3
"""
scripts/refresh_seed.py  —  make refresh-seed

Refresh the bundled corpora/ seed from what the live site is actually
serving, and stage the result without committing.

WHY THIS EXISTS
---------------
corpora/ is a seed, not the live content.  On Render the editable corpora
live on a persistent disk at /data, seeded from corpora/ on first boot and
authoritative from then on, so a curator's edits never reach this repository
by themselves.  The two drift apart silently and continuously.  On
18 September 2026 the gap had reached 67 records, and the bundled copy still
contained material that had been withdrawn from the live site three weeks
earlier.

WHAT IT DOES
------------
  * pulls the deployment's own corpora via GET /admin/backup
  * FAQ corpus: keeps only faq_ and fix_ records.  der_ and pam_ chunks are
    unreviewed drafts; they cannot answer a visitor on the live site and are
    not published here either, because nobody has read them
  * museums.jsonl: clears any tour_url, which still points at a withdrawn
    page that 404s
  * refreshes every other corpus the deployment holds a copy of
  * prints a per-file diff and validates the result
  * stages the changes and stops, so a person reads the diff before it
    becomes history

It never commits and never pushes.

USAGE
-----
    export SUBDOCENT_BASE_URL=https://submarinedocent.org
    export ADMIN_USERNAME=... ADMIN_PASSWORD=...
    make refresh-seed              # or: --dry-run to look without writing

Credentials come from the environment only, never from arguments, which
would put them in shell history and process listings.
"""

import argparse
import base64
import io
import json
import os
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPORA = os.path.join(REPO, "corpora")

ANSWERABLE_PREFIXES = ("faq_", "fix_")
DEFAULT_BASE_URL = "https://submarinedocent.org"


def env(name, default=None):
    v = os.getenv(name, "").strip()
    if not v and default is None:
        sys.exit(f"{name} is not set. Export it; this script never takes it as an argument.")
    return v or default


def fetch_backup(base, auth):
    req = urllib.request.Request(base.rstrip("/") + "/admin/backup")
    req.add_header("Authorization", "Basic " + auth)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            if r.status != 200:
                sys.exit(f"GET /admin/backup returned {r.status}")
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"GET /admin/backup returned {e.code}: {e.read()[:200]!r}")
    except Exception as e:
        sys.exit(f"GET /admin/backup failed: {type(e).__name__}: {e}")


def load_jsonl_text(text):
    return [json.loads(l) for l in text.splitlines() if l.strip()]


def key_of(record):
    return str(record.get("chunk_id") or record.get("id") or "")


def transform(filename, records):
    """Per-file rules. Returns (records, note)."""
    if filename == "dieselsubs_faq_corpus.jsonl":
        kept = [r for r in records if key_of(r).startswith(ANSWERABLE_PREFIXES)]
        return kept, f"{len(records) - len(kept)} unreviewed drafts withheld"
    if filename == "museums.jsonl":
        n = 0
        for r in records:
            if (r.get("tour_url") or "").strip():
                r["tour_url"] = None
                n += 1
        return records, (f"{n} withdrawn tour_url cleared" if n else "")
    return records, ""


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args],
                          capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.getenv("SUBDOCENT_BASE_URL", DEFAULT_BASE_URL))
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would change; write and stage nothing")
    args = ap.parse_args()

    # A refresh tangled up with hand edits is unreviewable: the diff stops
    # saying which change came from the live site and which came from a person.
    dirty = git("status", "--porcelain", "corpora")
    if dirty and not args.dry_run:
        print("corpora/ has uncommitted changes:\n" +
              "\n".join("  " + l for l in dirty.splitlines()))
        sys.exit("\nCommit or stash them first, so this refresh is the only thing in the diff.")

    auth = base64.b64encode(
        f"{env('ADMIN_USERNAME')}:{env('ADMIN_PASSWORD')}".encode()).decode()
    print(f"source : {args.base_url}")
    blob = fetch_backup(args.base_url, auth)
    print(f"         {len(blob):,} bytes\n")

    changed, unshipped, rows = [], [], []
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        members = {os.path.basename(m.name): m for m in tar.getmembers()
                   if m.name.endswith(".jsonl")}
        for filename in sorted(members):
            local = os.path.join(CORPORA, filename)
            if not os.path.exists(local):
                unshipped.append(filename)
                continue
            live = load_jsonl_text(tar.extractfile(members[filename]).read().decode("utf-8"))
            live, note = transform(filename, live)
            have = load_jsonl_text(open(local, encoding="utf-8").read())

            live_keys, have_keys = {key_of(r) for r in live}, {key_of(r) for r in have}
            added, removed = live_keys - have_keys, have_keys - live_keys
            by_key = {key_of(r): r for r in have}
            edited = sum(1 for r in live
                         if key_of(r) in have_keys and by_key[key_of(r)] != r)

            if not (added or removed or edited):
                rows.append((filename, len(have), len(live), 0, 0, 0, "unchanged"))
                continue
            rows.append((filename, len(have), len(live), len(added), len(removed), edited, note))
            changed.append((filename, local, live, sorted(added)[:4], sorted(removed)[:4]))

    print(f"{'FILE':<34}{'WAS':>6}{'NOW':>6}{'+':>5}{'-':>5}{'~':>5}  NOTE")
    for f, was, now, a, r, e, note in rows:
        print(f"  {f:<32}{was:>6}{now:>6}{a:>5}{r:>5}{e:>5}  {note}")
    if unshipped:
        print("\non the live disk but not shipped in corpora/ (ignored):")
        for f in unshipped:
            print(f"  {f}")

    if not changed:
        print("\nAlready in step with the live site. Nothing to do.")
        return

    for f, _p, _recs, added, removed in changed:
        if added or removed:
            print(f"\n  {f}")
            if added:
                print(f"    added   : {', '.join(added)}{' ...' if len(added) == 4 else ''}")
            if removed:
                print(f"    removed : {', '.join(removed)}{' ...' if len(removed) == 4 else ''}")

    if args.dry_run:
        print("\nDRY RUN. Nothing written.")
        return

    for filename, local, records, _a, _r in changed:
        with open(local, "w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Validate what was just written, not what we meant to write.
    faq_path = os.path.join(CORPORA, "dieselsubs_faq_corpus.jsonl")
    cat_path = os.path.join(CORPORA, "dieselsubs_faq_categories.jsonl")
    problems = []
    if os.path.exists(faq_path):
        faq = load_jsonl_text(open(faq_path, encoding="utf-8").read())
        stowaways = [key_of(r) for r in faq if not key_of(r).startswith(ANSWERABLE_PREFIXES)]
        if stowaways:
            problems.append(f"{len(stowaways)} unreviewed record(s) in the FAQ corpus: "
                            f"{', '.join(stowaways[:5])}")
        if os.path.exists(cat_path):
            # FAQ records name their category as a string, so the two files are a
            # matched pair: refresh one without the other and every record points
            # at a category that does not exist.
            defined = {(c.get("title") or c.get("name") or "").strip()
                       for c in load_jsonl_text(open(cat_path, encoding="utf-8").read())}
            used = {(r.get("category") or "").strip() for r in faq if (r.get("category") or "").strip()}
            missing = sorted(used - defined)
            if missing:
                problems.append(f"category referenced but not defined: {', '.join(missing)}")
            print(f"\ncategory integrity: {len(used)} referenced, {len(defined)} defined, "
                  f"{'none dangling' if not missing else 'DANGLING'}")

    if problems:
        print("\nVALIDATION FAILED — files written but NOT staged:")
        for p in problems:
            print(f"  {p}")
        sys.exit(1)

    paths = [os.path.relpath(p, REPO) for _f, p, _r, _a, _rm in changed]
    subprocess.run(["git", "-C", REPO, "add", *paths], check=True)
    print(f"\nStaged {len(paths)} file(s). Nothing committed.")
    print("Read the diff, then commit:\n  git diff --cached corpora/")


if __name__ == "__main__":
    main()
