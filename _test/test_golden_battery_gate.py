#!/usr/bin/env python3
"""CI gate: golden visitor-question battery must score at least PASS_FLOOR.

Run with:
    CONTENT_ROOT=corpora python3 _test/test_golden_battery_gate.py

Fails (exit 1) if fewer than PASS_FLOOR questions are answered correctly.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

GOLDEN = os.path.join(REPO, "_test", "golden_visitor_questions.jsonl")
# 2 Oct 2026: 7 pam_-derived fix_ records removed; raise to at least 65 when replacements land.
# (Was 62: 51/99 before patch 2026-10-01; floor set at post-patch score.)
PASS_FLOOR = 60


def main() -> int:
    import json
    from api import main as m

    with open(GOLDEN) as fh:
        questions = [json.loads(line) for line in fh if line.strip()]

    passed = 0
    for row in questions:
        q = row["question"]
        accept = set(row["accept"])
        hits = m.retrieve(question_text=q, compartment_id="",
                          playhead_time_ms=0, top_k=8)
        resp = m.synthesize_extractive(question_text=q, hits=hits) if hits else {}
        ids = [h[1].get("chunk_id") for h in hits]
        got = resp.get("faq_id") or (ids[0] if ids else None)
        # Rows that should refuse carry accept: ["refusal"].
        if not hits or (resp.get("refusal") or {}).get("is_refusal"):
            got = "refusal"
        if got in accept:
            passed += 1

    total = len(questions)
    print(f"  {passed}/{total} golden questions answered correctly "
          f"(floor: {PASS_FLOOR})")
    if passed < PASS_FLOOR:
        print(f"  FAIL: below floor of {PASS_FLOOR}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
