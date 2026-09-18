"""Batch 8 evaluation: probe 30 new questions."""
import json, ssl, urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

QUESTIONS = [
    "What did the captain do during a depth charge attack?",
    "How did the crew communicate with each other inside the submarine?",
    "What did crew members wear on a submarine?",
    "What was the significance of being qualified in submarines?",
    "What was the submarine combat insignia patrol pin?",
    "How did the Pampanito's crew perform the POW rescue from the water?",
    "What was the XO executive officers role on a submarine?",
    "What were the daily duties of the captain of a submarine?",
    "How did the crew handle a torpedo that malfunctioned?",
    "What happened to Japanese submarines at the end of the war?",
    "Did any American submarines get captured by the enemy?",
    "What was a ballast tank on a submarine?",
    "How did submarines navigate at night on the surface?",
    "What was a war patrol report?",
    "What were battle stations on a submarine?",
    "What was the role of the pharmacists mate on a submarine?",
    "How did the crew maintain the diesel engines?",
    "Could submarines communicate with each other while submerged?",
    "How did submarines avoid enemy minefields?",
    "What was a fleet boat?",
    "What happened if a crew member died while on patrol?",
    "What was commissioning day like for a new submarine?",
    "How did the Pampanito end up at Pier 45 in San Francisco?",
    "Were any of the Pampanito crew members famous?",
    "How did submarines get their orders for each war patrol?",
    "What was the sound of a torpedo being fired?",
    "How did submarines recharge their batteries?",
    "What was the job of the quartermaster on a submarine?",
    "How did submarines handle the threat from enemy destroyers?",
    "What was the difference between a Gato and a Balao class submarine?",
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
        cid = resp.get("faq_id") or "(tour)"
        short = (resp.get("answer_short") or "")[:90]
        print(f"Q{i+1:02d} [{cid:28s}] {q[:60]}")
        print(f"     → {short[:85]}")
        print()
    except Exception as e:
        print(f"Q{i+1:02d} ERROR: {e}")
