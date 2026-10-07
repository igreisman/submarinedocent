#!/usr/bin/env python3
"""A "when" question finds the "When ..." record, and "where" the "Where ...".

"when" and "where" are stopwords, so "When was the Pampanito built?" and
"Where was the Pampanito built?" are the same search, and a visitor asking
"when was pampanito built" was told where (6 October 2026).  A title that
opens with the question's own when or where now gets a small edge.

    CONTENT_ROOT=corpora python3 _test/test_question_words.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
TEST = {"X-SubDocent-Test": "1"}   # keeps these out of the visitor question log
failures = []

CASES = [
    ("when was pampanito built", "faq_1337"),     # When was the Pampanito built?
    ("where was pampanito built", "faq_1336"),    # Where was the Pampanito built?
]


def main() -> int:
    from api import main as m
    from fastapi.testclient import TestClient
    client = TestClient(m.app)
    for q, want in CASES:
        r = client.post("/ask", json={"question_text": q, "compartment_id": "", "playhead_time_ms": 0},
                        headers=TEST)
        got = r.json().get("faq_id") if r.status_code == 200 else f"http {r.status_code}"
        if got != want:
            print(f"  FAIL  {q!r}: got {got}, want {want}")
            failures.append(q)
    print(f"  {len(CASES) - len(failures)}/{len(CASES)} when/where questions find their record")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
