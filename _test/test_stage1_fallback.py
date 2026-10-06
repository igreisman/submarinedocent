#!/usr/bin/env python3
"""Questions no record answers get an honest fallback, and the docents hear of them.

On 5 October 2026 a visitor asked "Why was the sail fairwater cut down?" and
was answered from a record about the hull cuts, which never mentions the
fairwater.  The site now refuses when the record it would answer with leaves
7.0 or more of the question's word weight unexplained, says so in plain words,
and logs the question (date only) so a record can be written.

A visitor's preamble ("My grandfather served on a sub. How deep could they
dive?") is not searched; a boat it names is.

    CONTENT_ROOT=corpora python3 _test/test_stage1_fallback.py
"""
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

TEST = {"X-SubDocent-Test": "1"}   # keeps these out of the visitor question log
failures = []

# Questions no record answers.  CaptRackham's two, then the off-topic battery
# rows the floor catches.
MUST_FALL_BACK = [
    "Why was the sail fairwater cut down?",
    "Why did the superstructure shape change during the war?",
    "Can you recommend a good pizza place nearby?",
    "Who won the World Series last year?",
    "How do I reset my phone password?",
    "Is a yellow submarine better than a blue one?",
    "Can a submarine fly if you give it wings?",
]

# Off-topic rows still answered, 6 October 2026.  Their unusual words are in
# some record ("San Francisco" and "Australia" in Pampanito's history, "joke"
# in the cocktail-glass record).  Reported, not failed: a change either way
# should be noticed and recorded in the Stage 1 plan.
KNOWN_GAPS = [
    "What's the weather in San Francisco today?",
    "What is the capital of Australia?",
    "What's your favorite color?",
    "Tell me a joke about pirates",
    "Do fish ever get lost at sea?",
]

# A preamble must not change the answer.
CHATTY = [
    ("My grandfather served on a sub in the Pacific. How deep could they dive?",
     "How deep could the sub dive?"),
    ("I'm visiting with my kids this weekend and they keep asking me. How many men were in the crew?",
     "How many men were in the crew?"),
    ("Just curious, I've always wondered about this. How long were war patrols?",
     "How long were war patrols?"),
    ("We watched a documentary last night and it got us talking. How did Pampanito rescue POWs?",
     "How did Pampanito rescue POWs?"),
    ("My uncle was a torpedoman and never talked about it. What was the Mark 14 torpedo?",
     "What was the Mark 14 torpedo?"),
    ("I'm thinking about writing a school report on this topic. How were submarine sailors selected?",
     "How were submarine sailors selected?"),
    ("Sorry if this is a dumb question, I'm new to all this. Did anyone die while on the Pampanito?",
     "Did anyone die while on the Pampanito?"),
    ("Hello! I grew up near Cleveland and visited as a kid. What did USS Cod sink during the war?",
     "What did USS Cod sink during the war?"),
    ("My family is driving through Ohio next summer, so I was wondering. Why is there a WWII submarine in Cleveland?",
     "Why is there a WWII submarine in Cleveland?"),
    ("Okay so here is something I read online that confused me a bit. What happened with the Dutch submarine O-19?",
     "What happened with the Dutch submarine O-19?"),
]

# A boat named only in the preamble still picks the boat.
BOAT_IN_PREAMBLE = [
    ("My uncle served on Cod. What did his boat sink?", "faq_1367"),
    ("My uncle served on Pampanito. What did his boat sink?", "faq_1360"),
]


def check(label, ok, detail=""):
    if not ok:
        print(f"  FAIL  {label}  {detail}")
        failures.append(label)


def main() -> int:
    from api import main as m
    from fastapi.testclient import TestClient
    client = TestClient(m.app)

    def ask(q, headers=TEST):
        r = client.post("/ask", json={"question_text": q, "compartment_id": "", "playhead_time_ms": 0},
                        headers=headers)
        if r.status_code != 200:
            return "http %d" % r.status_code, {}
        d = r.json()
        ref = d.get("refusal") or {}
        if ref.get("reason") == "fallback":
            return "fallback", d
        return ("refusal" if ref.get("is_refusal") else d.get("faq_id")), d

    for q in MUST_FALL_BACK:
        got, d = ask(q)
        check(f"falls back: {q!r}", got == "fallback", f"got {got}")
        if got == "fallback":
            check(f"fallback text: {q!r}", d.get("answer_short") == m.FALLBACK_ANSWER)

    gaps = [(q, ask(q)[0]) for q in KNOWN_GAPS]
    closed = [q for q, got in gaps if got in ("fallback", "refusal")]
    if closed:
        print(f"  NOTE  known gaps now refused, record it in the Stage 1 plan: {closed}")

    for chatty, plain in CHATTY:
        got, _ = ask(chatty)
        want, _ = ask(plain)
        check(f"preamble ignored: {chatty[:50]!r}", got == want, f"got {got}, plain form {want}")

    for q, want in BOAT_IN_PREAMBLE:
        got, _ = ask(q)
        check(f"boat carried: {q!r}", got == want, f"got {got}")

    # A question that leans on its preamble keeps it.
    q = "There was a small box in the control room that recorded temperatures.  What was that for?"
    check("short question keeps its preamble", m._question_part(q) == q.strip())
    check("initials do not split a sentence",
          m._question_part("What did U. S. submarines do in WW2?") == "What did U. S. submarines do in WW2?")

    # The log: one line per fallback, date only, with what the docents need.
    saved = m.ASK_LOG_PATH
    with tempfile.TemporaryDirectory() as tmp:
        m.ASK_LOG_PATH = os.path.join(tmp, "ask_log.jsonl")
        try:
            ask("Why was the sail fairwater cut down?", headers={})
            ask("How many men were in the crew?", headers={})
            ask("Why was the sail fairwater cut down?")      # test traffic: not logged
            lines = [json.loads(l) for l in open(m.ASK_LOG_PATH, encoding="utf-8") if l.strip()]
        finally:
            m.ASK_LOG_PATH = saved
    check("two visitor lines logged, test traffic not", len(lines) == 2, f"got {len(lines)}")
    if len(lines) == 2:
        fb, ok = lines
        check("fallback logged as fallback", fb.get("faq_id") == "fallback", str(fb))
        check("fallback line keys", set(fb) == {"q", "faq_id", "museum_id", "date",
                                                "top_id", "top_score", "unexplained"}, str(sorted(fb)))
        check("date only, no time", len(fb.get("date", "")) == 10, fb.get("date", ""))
        check("unexplained at or over the floor", (fb.get("unexplained") or 0) >= m.MAX_UNEXPLAINED_IDF, str(fb))
        check("answered line unchanged", set(ok) == {"q", "faq_id", "museum_id", "date"}, str(sorted(ok)))

    print(f"  {len(MUST_FALL_BACK)} fall back, {len(CHATTY)} chatty, {len(BOAT_IN_PREAMBLE)} boat carries, "
          f"{len(KNOWN_GAPS) - len(closed)}/{len(KNOWN_GAPS)} known gaps still open: "
          f"{'OK' if not failures else str(len(failures)) + ' FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
