#!/usr/bin/env python3
"""Test batch 6 — 30 questions."""
import json, urllib.request, ssl, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# (question, expected_id_or_None)
TESTS = [
    ("What kind of food did the crew eat on a submarine?", "pam_088"),
    ("What was a submarine tender?", "pam_089"),
    ("What does the SS stand for in USS Pampanito SS-383?", "pam_090"),
    ("What was the hull number of the Pampanito?", "pam_105"),
    ("What was the forward torpedo room like?", None),          # tour OK
    ("What were the Japanese ships that were carrying the prisoners of war?", None),  # tour OK
    ("How did the crew know the survivors in the water were Allied prisoners?", "pam_091"),
    ("How did submarines handle medical emergencies at sea?", "pam_107"),
    ("Were there doctors on submarines?", "pam_092"),
    ("What was submarine school?", "pam_093"),
    ("Where did submariners go to train?", None),               # pam_028 OK
    ("What was Groton Connecticut?", "pam_093"),
    ("What was the SJ radar on a submarine?", "pam_094"),
    ("How did radar work on a WWII submarine?", "pam_110"),
    ("What was the Pacific Fleet submarine war strategy?", "pam_103"),
    ("How did submarines contribute to winning the war?", "pam_095"),
    ("How did submarines get their patrol assignments?", "pam_096"),
    ("What happened to enemy ships that were sunk?", None),     # tour/general OK
    ("Was the Pampanito ever damaged in combat?", "pam_097"),
    ("Did the Pampanito ever hit a mine?", "pam_108"),
    ("What was the Pampanito doing at the end of the war?", "pam_098"),
    ("What was the commissioning of a submarine?", "pam_100"),
    ("What was the decommissioning of the Pampanito?", "pam_109"),
    ("How was the Pampanito preserved as a museum?", "pam_099"),
    ("Who donated the Pampanito to the museum?", "pam_111"),
    ("What is the National Maritime Museum in San Francisco?", None),  # pam_022/099 OK
    ("What are the awards and decorations the Pampanito received?", "pam_081"),
    ("How did a submarine get resupplied at sea?", "pam_104"),
    ("What was the longest any submarine stayed submerged?", "pam_112"),
    ("Were there any mutinies or discipline problems on submarines?", "pam_102"),
]

def ask(q):
    data = json.dumps({"question_text": q, "lang": "en"}).encode()
    req = urllib.request.Request(
        "https://localhost:8443/ask", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        return json.loads(r.read())

# Wait for server
for _ in range(10):
    try:
        with urllib.request.urlopen(
            urllib.request.Request("https://localhost:8443/health"),
            context=ctx, timeout=3
        ) as r:
            d = json.loads(r.read())
            if d.get("faq_chunks", 0) >= 344:
                print(f"Server up ({d['faq_chunks']} FAQs)\n")
                break
    except Exception:
        time.sleep(1)

pass_count = fail_count = 0
fails = []

for q, expected in TESTS:
    try:
        d = ask(q)
        got = d.get("faq_id") or (d.get("citations") or [{}])[0].get("chunk_id") or "tour"
        ok = (expected is None or got == expected)
        if ok:
            pass_count += 1
            print(f"PASS [{got:20s}] {q[:60]}")
        else:
            fail_count += 1
            fails.append((q, expected, got))
            print(f"FAIL [{got:20s}] exp={expected} {q[:55]}")
    except Exception as e:
        fail_count += 1
        fails.append((q, "?", f"ERROR:{e}"))
        print(f"ERR  {q[:60]}")

print(f"\n{pass_count}/{len(TESTS)} PASS, {fail_count} FAIL")
if fails:
    print("\nFailed:")
    for q, exp, got in fails:
        print(f"  exp={exp}, got={got}: {q}")
