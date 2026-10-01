#!/usr/bin/env python3
"""Run the 99-question golden battery and report pass/fail per question.

Usage:
    CONTENT_ROOT=corpora python3 _test/run_golden_battery.py [golden.jsonl]

Exits 0 only when all questions pass (for use as a gate in CI after confirming
the expected count).  Prints a full diff suitable for before/after comparison.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

DEFAULT_GOLDEN = os.path.join(
    REPO, "_test", "golden_visitor_questions.jsonl"
)


def main(golden_path: str | None = None) -> int:
    golden_path = golden_path or DEFAULT_GOLDEN
    from api import main as m

    with open(golden_path) as fh:
        questions = [json.loads(line) for line in fh if line.strip()]

    passed, failed = [], []
    for row in questions:
        q = row["question"]
        accept = set(row["accept"])
        hits = m.retrieve(question_text=q, compartment_id="",
                          playhead_time_ms=0, top_k=8)
        ids = [h[1].get("chunk_id") for h in hits]
        resp = m.synthesize_extractive(question_text=q, hits=hits) if hits else {}
        got = resp.get("faq_id") or (ids[0] if ids else None)
        ok = got in accept
        entry = {"q": q, "got": got, "accept": sorted(accept)}
        if ok:
            passed.append(entry)
        else:
            failed.append(entry)

    total = len(questions)
    print(f"\n  {len(passed)}/{total} golden questions answered correctly\n")

    if failed:
        print("  FAILING:")
        for e in failed:
            print(f"    {e['q']!r}")
            print(f"      got:    {e['got']}")
            print(f"      accept: {e['accept']}")
        print()

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
