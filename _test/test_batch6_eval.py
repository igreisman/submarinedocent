#!/usr/bin/env python3
"""Batch 6 evaluation — 30 new questions, prints answer text for human review."""
import json, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

QUESTIONS = [
    "What kind of food did the crew eat on a submarine?",
    "What was a submarine tender?",
    "What does the SS stand for in USS Pampanito SS-383?",
    "What was the hull number of the Pampanito?",
    "What was the forward torpedo room like?",
    "What were the Japanese ships that were carrying the prisoners of war?",
    "How did the crew know the survivors in the water were Allied prisoners?",
    "How did submarines handle medical emergencies at sea?",
    "Were there doctors on submarines?",
    "What was submarine school?",
    "Where did submariners go to train?",
    "What was Groton Connecticut?",
    "What was the SJ radar on a submarine?",
    "How did radar work on a WWII submarine?",
    "What was the Pacific Fleet submarine war strategy?",
    "How did submarines contribute to winning the war?",
    "How did submarines get their patrol assignments?",
    "What happened to enemy ships that were sunk?",
    "Was the Pampanito ever damaged in combat?",
    "Did the Pampanito ever hit a mine?",
    "What was the Pampanito doing at the end of the war?",
    "What was the commissioning of a submarine?",
    "What was the decommissioning of the Pampanito?",
    "How was the Pampanito preserved as a museum?",
    "Who donated the Pampanito to the museum?",
    "What is the National Maritime Museum in San Francisco?",
    "What are the awards and decorations the Pampanito received?",
    "How did a submarine get resupplied at sea?",
    "What was the longest any submarine stayed submerged?",
    "Were there any mutinies or discipline problems on submarines?",
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

print(f"{'#':<3} {'QUESTION':<52} {'TOP_ID':<16} ANSWER_SHORT")
print("-" * 130)
for i, q in enumerate(QUESTIONS, 1):
    try:
        d = ask(q)
        top = d.get("faq_id") or (d.get("citations") or [{}])[0].get("chunk_id") or "—"
        is_refusal = d.get("refusal", {}).get("is_refusal", False)
        ans = d.get("answer_short", "")[:80].replace("\n", " ")
        flag = "MISS" if is_refusal else "    "
        print(f"{flag} {i:<3} {q:<52} {top:<16} {ans}")
    except Exception as e:
        print(f"ERR  {i:<3} {q:<52} ERROR: {e}")
