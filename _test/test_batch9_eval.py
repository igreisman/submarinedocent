"""Batch 9 evaluation — 30 new questions, print faq_id + answer_short for each."""
import json, ssl, urllib.request, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

QUESTIONS = [
    "What was the control room used for on a submarine?",
    "What did the forward torpedo room look like?",
    "How did the crew dispose of garbage on a submarine?",
    "What happened to enemy survivors after a submarine attack?",
    "What was a hydrophone on a submarine?",
    "How did submarines handle fires or flooding emergencies?",
    "What was a periscope feather?",
    "How did the crew avoid boredom on a long patrol?",
    "What was the role of the TDC operator?",
    "What happened if a submarine ran aground?",
    "How did submarines in a wolfpack coordinate their attacks?",
    "What was a trim dive on a submarine?",
    "What did a Japanese convoy look like?",
    "How did the Pampanito earn her battle stars?",
    "How long did it take to reload a torpedo tube?",
    "What was the flying bridge on a submarine?",
    "How deep could the Pampanito dive?",
    "What was the magnetic exploder problem with US torpedoes?",
    "Who was the most successful US submarine commander of WWII?",
    "How did the crew celebrate after a successful attack?",
    "What did submariners do when they returned to port?",
    "How many US submarines were lost in WWII?",
    "Why were submarines called the Silent Service?",
    "How did submarine construction change during the war?",
    "What was the maneuvering room on a submarine?",
    "What was a crash dive?",
    "How long did it take to build a submarine?",
    "What was a snorkel on a submarine?",
    "How did radar work on a submarine?",
    "What was the periscope depth on a submarine?",
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
