"""Batch 10 evaluation — 30 new questions."""
import json, ssl, urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

QUESTIONS = [
    "What was the officer of the deck responsible for?",
    "How did submarines navigate without GPS?",
    "What was a conning tower on a submarine?",
    "How were new submarine crew members trained?",
    "What was a sound-powered telephone?",
    "How did submarines identify enemy ships at night?",
    "What was the after torpedo room used for?",
    "How did the Navy decide which men could serve on submarines?",
    "What happened to a submarine crew if the boat was sunk?",
    "How did submarines handle bad weather on the surface?",
    "What was a down angle on a submarine?",
    "How did submarines attack targets at night?",
    "What was the torpedo data computer made of?",
    "What did the lookouts on a submarine watch for?",
    "How were submarines refueled in the Pacific?",
    "What was a target's angle on the bow?",
    "How did submarines communicate with Pearl Harbor?",
    "What was the after engine room on a submarine?",
    "How many torpedoes did the Pampanito carry?",
    "What was the purpose of the forward engine room?",
    "How did submarines find their patrol areas?",
    "What was a submarine tender?",
    "How did submarine captains decide when to surface?",
    "What was the escape hatch on a submarine used for?",
    "How did sonar operators track enemy ships?",
    "What was the role of the chief of the boat on a submarine?",
    "How did torpedo spreads work?",
    "What was a submarine's test depth?",
    "How did submarines avoid collision with each other?",
    "What was a night periscope attack?",
]

def ask(q):
    data = json.dumps({"question_text": q, "lang": "en"}).encode()
    req = urllib.request.Request(
        "https://localhost:8443/ask", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        return json.loads(r.read())

for i, q in enumerate(QUESTIONS, 1):
    try:
        resp = ask(q)
        fid = resp.get("faq_id") or "(tour)"
        ans = (resp.get("answer_short") or "").replace("\n", " ")[:90]
        print(f"Q{i:02d} {fid:30s} {q[:55]}")
        print(f"     → {ans}")
    except Exception as e:
        print(f"Q{i:02d} ERROR: {e}")
