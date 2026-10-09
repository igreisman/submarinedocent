#!/usr/bin/env python3
"""One- and two-word questions, the 1946 manual, and the boat boost.

In the 6 October visitor log, 13 of the 22 one- and two-word questions that
were answered got the wrong record ("dirty", "deck", "uss razorback"), and
eight single words were answered from the 1946 Fleet Type manual about
something else ("floor" was a vent pipe).  A short question now gets a prompt
to ask in full, with the records its words best match as suggestions, and the
manual never answers one.  "How many torpedoes does the Pampanito carry?" went
to "When was the Pampanito built?", the boat boost lifting a record that shared
only the boat's name; the boost now needs the record to match the rest.

    CONTENT_ROOT=corpora python3 _test/test_short_queries.py
"""
import os
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

    def ask(q, **extra):
        r = client.post("/ask", json=dict({"question_text": q, "compartment_id": "", "playhead_time_ms": 0}, **extra),
                        headers=TEST)
        return r.json() if r.status_code == 200 else {"status": r.status_code}

    # 1. Short questions: a prompt, with suggestions that each name a record.
    d = ask("showers")
    check("one word gets the prompt", (d.get("refusal") or {}).get("reason") == "short_query", str(d.get("refusal")))
    check("prompt text", d.get("answer_short") == m.SHORT_QUERY_ANSWER, repr(d.get("answer_short")))
    sug = d.get("suggestions") or []
    answerable = {c["chunk_id"] for c in m.FAQ}
    check("up to three suggestions, each an answerable record with its title",
          0 < len(sug) <= 3 and all(s["faq"] in answerable and s["q"] for s in sug), repr(sug))
    check("a suggestion, sent back with its id, answers from that record",
          bool(sug) and ask(sug[0]["q"], faq_id=sug[0]["faq"]).get("faq_id") == sug[0]["faq"])
    d = ask("uss razorback")
    check("two words get the prompt", (d.get("refusal") or {}).get("reason") == "short_query")
    d = ask("sex")
    check("no match: the prompt alone, no suggestions",
          d.get("answer_short") == m.SHORT_QUERY_ANSWER_ALONE and not d.get("suggestions"), repr(d.get("answer_short")))
    d = ask("what's a deck?")
    check("three words are answered as usual", (d.get("refusal") or {}).get("reason") != "short_query")
    pinned = ask("Doctor", faq_id="faq_1136")
    check("a pinned one-word balloon still answers from its record", pinned.get("faq_id") == "faq_1136")

    # 2. The manual never answers a short question, even with the prompt off.
    saved = m.SHORT_QUERY_PROMPT
    m.SHORT_QUERY_PROMPT = False
    try:
        for q in ("floor", "watts", "dirt"):
            d = ask(q)
            cites = [c.get("chunk_id", "") for c in d.get("citations") or []]
            check(f"{q!r} is not answered from the manual", not any(c.startswith("fsm_") for c in cites), repr(cites))
        d = ask("What is a drain pump for")
        cites = [c.get("chunk_id", "") for c in d.get("citations") or []]
        check("a full question may still be answered from the manual",
              any(c.startswith("fsm_") for c in cites), repr(cites))
    finally:
        m.SHORT_QUERY_PROMPT = saved

    # 3. The boat boost needs the record to match more than the boat's name.
    d = ask("How many torpedoes does the Pampanito carry?")
    check("torpedo count, not the build date", d.get("faq_id") == "faq_1220", d.get("faq_id"))
    d = ask("what ships did the Pampanito sink")
    check("the Reddit question keeps its record", d.get("faq_id") == "faq_1360", d.get("faq_id"))

    print(f"  short queries, manual, boat boost: {'OK' if not failures else str(len(failures)) + ' FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
