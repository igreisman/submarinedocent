#!/usr/bin/env python3
"""Test batch 5: 30 questions with expected FAQ IDs for the ones we know."""
import json, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# (question, expected_faq_id_or_None_if_tour_ok)
TESTS = [
    ("How many torpedoes did a submarine carry?", "pam_067"),
    ("What types of ships did submarines target?", None),          # tour OK
    ("What was the temperature like inside a submarine?", "pam_068"),
    ("How loud was it inside a submarine?", "pam_069"),
    ("What rank was the captain of a submarine?", None),           # existing FAQ OK
    ("How long was a typical war patrol?", "pam_070"),
    ("What did the crew do when they spotted an enemy ship?", "pam_071"),
    ("Did submarines ever fight other submarines?", "pam_072"),
    ("What happened if a submarine got stuck on the bottom?", "pam_083"),
    ("What was the largest submarine in WWII?", "pam_073"),
    ("How many patrols did the Pampanito go on?", None),           # existing FAQ OK
    ("Did submarines ever carry troops or special forces?", "pam_074"),
    ("What was a war patrol?", "pam_075"),
    ("How far could a submarine travel on one fuel load?", "pam_087"),
    ("What was the diving alarm sound?", "pam_084"),
    ("How did the crew handle doing laundry?", "pam_076"),
    ("Did the Pampanito crew get shore leave?", "pam_077"),
    ("How many ships did the Pampanito sink?", None),              # existing FAQ OK
    ("What ports did the Pampanito operate from?", "pam_078"),
    ("What was the control room of a submarine like?", None),      # tour OK
    ("How did sonar work on a WWII submarine?", None),             # pam_010 OK
    ("What was a Mark 14 torpedo?", "pam_079"),
    ("How did submarine crews track enemy ships?", "pam_086"),
    ("What was the battery room on a submarine?", "pam_085"),
    ("Who designed the Balao-class submarine?", None),             # generic OK
    ("How did submarines avoid detection?", None),                 # existing OK
    ("What was the torpedo data computer?", None),                 # pam_020 OK
    ("What happened to the crew after the war?", "pam_080"),
    ("Were any Pampanito crew members awarded medals?", "pam_081"),
    ("How much fuel did a submarine carry?", "pam_082"),
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

pass_count = 0
fail_count = 0
fails = []

for q, expected in TESTS:
    try:
        d = ask(q)
        got = d.get("faq_id") or (d.get("citations") or [{}])[0].get("chunk_id") or "tour"
        if expected is None or got == expected:
            pass_count += 1
            status = "PASS"
        else:
            fail_count += 1
            status = "FAIL"
            fails.append((q, expected, got))
        ans_short = d.get("answer_short","")[:60].replace("\n"," ")
        print(f"{status} [{got:12s}] {q[:55]:<55}  {ans_short}")
    except Exception as e:
        fail_count += 1
        fails.append((q, expected, f"ERROR:{e}"))
        print(f"FAIL [ERROR     ] {q[:55]}")

print(f"\n{pass_count}/{len(TESTS)} PASS, {fail_count} FAIL")
if fails:
    print("\nFailed:")
    for q, exp, got in fails:
        print(f"  expected={exp}, got={got}: {q}")
