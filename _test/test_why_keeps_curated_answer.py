#!/usr/bin/env python3
"""A "why" question keeps the FAQ record it retrieved.

synthesize_extractive used to check a "why" answer for a causal word
("because", "since", "aim" and others) and, finding none, rebuild the answer
from the first lower-ranked hit that had one.  181 answerable records use none
of those words, so a visitor who did not repeat the title word for word got a
neighbour's text: on 2 October 2026 "Why exactly is there a broom on the
periscope shears..." read faq_1170, on oxygen.

Each question here is a record's own title with "exactly" added, so the title
no longer covers the question.  These eight are the records whose titles first
showed the defect on 1 October.

    CONTENT_ROOT=corpora python3 _test/test_why_keeps_curated_answer.py
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

RECORDS = ["faq_1060", "faq_1092", "faq_1120", "faq_1122",
           "faq_1321", "faq_1340", "faq_1361", "faq_1371"]


def exactly(title: str) -> str:
    if title.lower().startswith("why "):
        return "Why exactly" + title[3:]
    return title.rstrip("?") + ", exactly?"


def main() -> int:
    from api import main as m

    by_id = {e.get("chunk_id"): e for e in m.FAQ}
    missing = [r for r in RECORDS if r not in by_id]
    if missing:
        print(f"  records not loaded: {missing}; is CONTENT_ROOT right?")
        return 1

    failed = []
    for cid in RECORDS:
        q = exactly(by_id[cid]["title"])
        hits = m.retrieve(question_text=q, compartment_id="", playhead_time_ms=0, top_k=8)
        resp = m.synthesize_extractive(question_text=q, hits=hits) if hits else {}
        got = resp.get("faq_id")
        if (resp.get("refusal") or {}).get("is_refusal"):
            got = "refusal"
        ok = got == cid
        print(f"  {'PASS' if ok else 'FAIL'}  {q!r} -> {got}")
        if not ok:
            failed.append(cid)

    print(f"\n  {len(RECORDS) - len(failed)}/{len(RECORDS)} \"why\" questions keep their own record")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
