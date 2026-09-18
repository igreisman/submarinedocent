"""Batch 7 evaluation: probe 30 new questions and see what the server returns."""
import json, ssl, urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

QUESTIONS = [
    "What was the lifeguard mission in WWII?",
    "Did the Pampanito participate in rescue operations for downed pilots?",
    "Did submarines ever lay mines?",
    "How did a depth charge attack feel inside a submarine?",
    "What was hot bunking on a submarine?",
    "How did the submarine deck gun work?",
    "How did the Pampanito get its name?",
    "What was the torpedo data computer?",
    "How did submarine crews handle a fire onboard?",
    "Did WWII American submarines have a snorkel?",
    "How did submarine crews celebrate after sinking a ship?",
    "What was the role of submarines at the Battle of Midway?",
    "What was radio direction finding and how did it threaten submarines?",
    "How did the crew deal with claustrophobia?",
    "What was the galley like on a submarine?",
    "How did submarine crews get fresh water?",
    "How many war patrols did the Pampanito complete?",
    "Was the Pampanito ever close to being sunk?",
    "What is the National Historic Landmark designation of the Pampanito?",
    "How did a submarine attack a convoy?",
    "What was a ping in submarine terms?",
    "How did the crew handle seasickness on a submarine?",
    "Did the Pampanito ever sink a Japanese warship?",
    "What were wolfpack tactics in WWII submarines?",
    "How many torpedoes did the Pampanito fire during the war?",
    "What is the difference between a trim dive and a normal dive?",
    "What was a submarine escape trunk?",
    "Were submarines used to land spies or special forces?",
    "How did submarines handle the threat of aircraft?",
    "What was the role of the executive officer on a submarine?",
]

def ask(q):
    data = json.dumps({"question_text": q, "lang": "en"}).encode()
    req = urllib.request.Request(
        "https://localhost:8443/ask", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        return json.loads(r.read())

for i, q in enumerate(QUESTIONS):
    try:
        resp = ask(q)
        cid = resp.get("faq_id", "—")
        short = resp.get("answer_short", "")[:80]
        print(f"Q{i+1:02d} [{cid:30s}] | {q[:60]}")
        print(f"     → {short}")
        print()
    except Exception as e:
        print(f"Q{i+1:02d} ERROR: {e}")
