import json, urllib.request, ssl, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def ask(q):
    body = json.dumps({"question_text": q, "compartment_id": ""}).encode()
    req = urllib.request.Request("https://localhost:8443/ask", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        return json.loads(r.read())

for i in range(12):
    try:
        ask("test")
        print(f"Server up ({i+1}s)")
        break
    except:
        time.sleep(1)
else:
    print("TIMEOUT"); exit()

questions = [
    ("How many people were in a WWII submarine crew?", "pam_035"),
    ("How many men were on a submarine?", "pam_059"),  # paraphrase alias - same content
    ("What did the crew do for fun on a long patrol?", "pam_036"),
    ("What was the toilet like on a submarine?", "pam_037"),
    ("How did you flush a toilet on a submarine?", "pam_064"),  # now has dedicated alias
    ("How did submarines surface from underwater?", "pam_038"),
    ("What was the procedure for an emergency dive?", "pam_039"),
    ("What is a crash dive?", "pam_060"),
    ("What is a periscope and how was it used?", "pam_040"),
    ("What is a conning tower?", "10_conning_tower_0004"),  # tour chunk is acceptable content
    ("How did they control the depth of the submarine?", "pam_042"),
    ("What were the biggest dangers for submarine crews?", "pam_043"),
    ("How many American submarines were lost in WWII?", "pam_061"),  # now has dedicated FAQ
    ("What caused the most submarine losses in WWII?", "pam_044"),
    ("Were American torpedo problems fixed during the war?", "pam_045"),
    ("Who was the captain of the Pampanito?", "pam_046"),
    ("How many patrols did the Pampanito complete?", "faq_1012"),
    ("What is the silent service?", "pam_047"),
    ("How old were the men who served on submarines?", "pam_048"),
    ("Were there African American sailors on WWII submarines?", "pam_049"),
    ("How did submarines get fuel and supplies during a patrol?", "pam_050"),
    ("What does it smell like inside a submarine?", "pam_051"),
    ("How did submarine crews get mail from home?", "pam_052"),
    ("What happened when a submarine returned to port?", "pam_053"),
    ("What is a wolf pack?", "pam_054"),
    ("Did submarines ever rescue people from the water?", "pam_062"),
    ("Did the Pampanito save POWs?", "pam_063"),
    ("What happened to men who were killed on a submarine patrol?", "pam_056"),
    ("What happened to the Japanese submarine force in WWII?", "pam_057"),
    ("How did US submarines compare to German U-boats?", "pam_058"),
]

print(f"\n{'RESULT':<6} {'GOT':<12} {'EXPECTED':<12} QUESTION")
print("-"*90)
pass_count = 0
fail_count = 0
fails = []
for q, expected in questions:
    r = ask(q)
    got = r.get("faq_id") or (r.get("citations") or [{}])[0].get("chunk_id","??")
    ok = got == expected
    if ok:
        pass_count += 1
        print(f"{'PASS':<6} {got:<12} {expected:<12} {q[:60]}")
    else:
        fail_count += 1
        fails.append((q, expected, got))
        print(f"{'FAIL':<6} {got:<12} {expected:<12} {q[:60]}")

print(f"\n{pass_count}/{len(questions)} PASS, {fail_count} FAIL")
if fails:
    print("\nFailed questions:")
    for q, exp, got in fails:
        print(f"  expected={exp}  got={got}  q={q}")
