#!/usr/bin/env python3
"""Batch 5 evaluation — 30 new questions, prints answer text for human review."""
import json, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

QUESTIONS = [
    "How many torpedoes did a submarine carry?",
    "What types of ships did submarines target?",
    "What was the temperature like inside a submarine?",
    "How loud was it inside a submarine?",
    "What rank was the captain of a submarine?",
    "How long was a typical war patrol?",
    "What did the crew do when they spotted an enemy ship?",
    "Did submarines ever fight other submarines?",
    "What happened if a submarine got stuck on the bottom?",
    "What was the largest submarine in WWII?",
    "How many patrols did the Pampanito go on?",
    "Did submarines ever carry troops or special forces?",
    "What was a war patrol?",
    "How far could a submarine travel on one fuel load?",
    "What was the diving alarm sound?",
    "How did the crew handle doing laundry?",
    "Did the Pampanito crew get shore leave?",
    "How many ships did the Pampanito sink?",
    "What ports did the Pampanito operate from?",
    "What was the control room of a submarine like?",
    "How did sonar work on a WWII submarine?",
    "What was a Mark 14 torpedo?",
    "How did submarine crews track enemy ships?",
    "What was the battery room on a submarine?",
    "Who designed the Balao-class submarine?",
    "How did submarines avoid detection?",
    "What was the torpedo data computer?",
    "What happened to the crew after the war?",
    "Were any Pampanito crew members awarded medals?",
    "How much fuel did a submarine carry?",
]

def ask(q):
    data = json.dumps({"question_text": q, "lang": "en"}).encode()
    req = urllib.request.Request(
        "https://localhost:8443/ask",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        return json.loads(r.read())

print(f"{'#':<3} {'QUESTION':<52} {'TOP_ID':<12} ANSWER_SHORT")
print("-" * 120)
for i, q in enumerate(QUESTIONS, 1):
    try:
        d = ask(q)
        top = d.get("faq_id") or (d.get("citations") or [{}])[0].get("chunk_id") or "tour"
        ans = d.get("answer_short", "")[:110]
        print(f"{i:<3} {q:<52} {top:<12} {ans}")
    except Exception as e:
        print(f"{i:<3} {q:<52} ERROR: {e}")
