#!/usr/bin/env python3
"""Field-level diff for JSONL corpus files.

Compares records by ID and prints only the fields that changed, plus any
records added or removed. Far more readable than `git diff` on long JSONL lines.

Usage:
  python3 scripts/diff_corpus.py                  # HEAD vs staged, all corpora/*.jsonl
  python3 scripts/diff_corpus.py --working        # HEAD vs working tree
  python3 scripts/diff_corpus.py --ref HEAD~3     # HEAD~3 vs staged
  python3 scripts/diff_corpus.py corpora/dieselsubs_faq_corpus.jsonl
"""
import argparse
import glob
import json
import subprocess
import sys

ID_KEYS = ("chunk_id", "id", "slug")


def git_show(spec):
    res = subprocess.run(["git", "show", spec], capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else ""


def record_id(rec, index):
    for k in ID_KEYS:
        if k in rec:
            return str(rec[k])
    return f"line {index + 1}"


def parse(text, label):
    records = {}
    for i, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"  ! {label} line {i + 1}: invalid JSON ({e})")
            continue
        records[record_id(rec, i)] = rec
    return records


def short(value, limit=300):
    s = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return s if len(s) <= limit else s[:limit] + " ..."


def diff_file(path, ref, working):
    old = parse(git_show(f"{ref}:{path}"), f"{ref}:{path}")
    if working:
        try:
            with open(path, encoding="utf-8") as f:
                new_text = f.read()
        except FileNotFoundError:
            new_text = ""
        new_label = "working tree"
    else:
        new_text = git_show(f":{path}")
        new_label = "staged"
    new = parse(new_text, f"{new_label}:{path}")

    added = [k for k in new if k not in old]
    removed = [k for k in old if k not in new]
    changed = [k for k in new if k in old and new[k] != old[k]]
    if not (added or removed or changed):
        return 0

    print(f"\n== {path}  ({ref} -> {new_label}): "
          f"{len(changed)} changed, {len(added)} added, {len(removed)} removed")
    for k in added:
        print(f"  + {k}: {short(new[k].get('title', ''))}")
    for k in removed:
        print(f"  - {k}: {short(old[k].get('title', ''))}")
    for k in changed:
        o, n = old[k], new[k]
        for field in sorted(set(o) | set(n)):
            if o.get(field) != n.get(field):
                print(f"  ~ {k}  {field}")
                print(f"      was: {short(o.get(field))}")
                print(f"      now: {short(n.get(field))}")
    return len(added) + len(removed) + len(changed)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="JSONL files (default: corpora/*.jsonl)")
    ap.add_argument("--ref", default="HEAD", help="git ref to compare from (default: HEAD)")
    ap.add_argument("--working", action="store_true",
                    help="compare against the working tree instead of the staged copy")
    args = ap.parse_args()

    files = args.files or sorted(glob.glob("corpora/*.jsonl"))
    if not files:
        sys.exit("No JSONL files found. Run from the repo root or pass file paths.")

    total = sum(diff_file(f, args.ref, args.working) for f in files)
    print(f"\n{total} record(s) differ." if total else "No record-level changes.")


if __name__ == "__main__":
    main()
