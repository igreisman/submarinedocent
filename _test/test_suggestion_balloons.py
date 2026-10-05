#!/usr/bin/env python3
"""Every suggested-question balloon returns the record it was written for.

Balloons used to send only their words to /ask, which searched them like any
typed question.  On 5 October 2026 a Reddit visitor clicked "What ships did
Pampanito sink?" and got a record about Japanese submarines; three other
balloons were also landing on the wrong record.  Each balloon now names its
record, and /ask answers from it.

    CONTENT_ROOT=corpora python3 _test/test_suggestion_balloons.py
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

TEST = {"X-SubDocent-Test": "1"}   # keeps these out of the visitor question log
failures = []


def check(label, ok, detail=""):
    if not ok:
        print(f"  FAIL  {label}  {detail}")
        failures.append(label)


def main() -> int:
    from api import main as m
    from fastapi.testclient import TestClient
    client = TestClient(m.app)

    def ask(body):
        body = dict({"compartment_id": "", "playhead_time_ms": 0}, **body)
        r = client.post("/ask", json=body, headers=TEST)
        return r.status_code, r.json()

    answerable = {c.get("chunk_id"): c for c in m.FAQ}
    if not answerable:
        print("  no answerable records loaded; is CONTENT_ROOT right?")
        return 1

    # 1. Ask the Docent's balloons, read from the page itself.
    page = open(os.path.join(REPO, "web", "askthedocent.html"), encoding="utf-8").read()
    block = page[page.index("const DEFAULT_SUGGESTIONS"):page.index("function showSuggestions")]
    balloons = re.findall(r"\{\s*q:\s*'([^']+)',\s*faq:\s*'([^']+)'\s*\}", block)
    check("Ask the Docent has balloons", len(balloons) >= 3, f"found {len(balloons)}")
    for q, fid in balloons:
        check(f"{fid} is answerable ({q})", fid in answerable)
        st, d = ask({"question_text": q, "faq_id": fid})
        check(f"balloon {q!r} returns {fid}", st == 200 and d.get("faq_id") == fid,
              f"got {st} {d.get('faq_id')}")
        check(f"balloon {q!r} is not a refusal", not (d.get("refusal") or {}).get("is_refusal"))

    # 2. Every answerable record can be reached by id, which is what museum
    #    chips rely on (they send the id of the record whose title they show).
    wrong = []
    for fid, rec in answerable.items():
        st, d = ask({"question_text": rec.get("title", ""), "faq_id": fid, "museum_id": str(rec.get("museum_id") or "")})
        if st != 200 or d.get("faq_id") != fid or (d.get("refusal") or {}).get("is_refusal"):
            wrong.append((fid, st, d.get("faq_id")))
    check(f"all {len(answerable)} records reachable by id", not wrong, str(wrong[:5]))

    # 3. An id that is not an answerable record falls back to an ordinary search.
    q = "How deep could Pampanito dive?"
    _, searched = ask({"question_text": q})
    _, fell_back = ask({"question_text": q, "faq_id": "faq_does_not_exist"})
    check("unknown id falls back to search", fell_back.get("faq_id") == searched.get("faq_id"),
          f"{fell_back.get('faq_id')} vs {searched.get('faq_id')}")

    print(f"  {len(balloons)} balloons, {len(answerable)} records by id: "
          f"{'OK' if not failures else str(len(failures)) + ' FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
