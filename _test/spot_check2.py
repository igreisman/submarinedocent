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

for i in range(15):
    try:
        ask("test"); print("UP"); break
    except: time.sleep(1)
else:
    print("TIMEOUT"); exit()

checks = [
    # Batch 1-3 spot checks
    ("How many torpedo reloads does the Pampanito carry?", "pam_006"),
    ("How could a submarine run underwater without air?", "pam_065"),  # now has alias
    ("Could a submarine run underwater without air?", "pam_065"),
    ("Why did submarines stay on the surface at night?", "pam_066"),  # now has alias
    ("Why were submarines on the surface at night?", "pam_066"),  # alias with same content
    ("How did submarines navigate without GPS?", "pam_009"),
    ("How many ships did the Pampanito sink?", "pam_012"),
    ("When was the Pampanito built?", "pam_013"),
    ("What is a depth charge?", "pam_015"),
    ("How did the crew breathe underwater?", "pam_018"),
    ("How did a torpedo work?", "pam_019"),
    ("How did the captain fire torpedoes?", "pam_021"),
    ("Where is the Pampanito?", "pam_022"),  # pam_024 fix should restore this
    ("What class of submarine is the Pampanito?", "pam_023"),
    ("What happened to the Pampanito after the war?", "pam_024"),
    ("How deep could a submarine dive?", "pam_025"),
    ("How fast could a submarine go?", "pam_026"),  # synonym fix should help
    ("How long did it take to train submarine crews?", "pam_028"),
    ("How could submariners escape a sinking submarine?", "pam_029"),
    ("Were women allowed on submarines in WWII?", "pam_031"),
    ("Were women on submarines in WWII?", "pam_031"),
]

print(f"\n{'RESULT':<6} {'GOT':<40} {'EXP':<12} QUESTION")
print("-"*100)
pass_c = fail_c = 0
fails = []
for q, exp in checks:
    r = ask(q)
    got = r.get("faq_id") or (r.get("citations") or [{}])[0].get("chunk_id","??")
    ok = got == exp
    pass_c += ok; fail_c += not ok
    if not ok: fails.append((q, exp, got))
    print(f"{'PASS' if ok else 'FAIL':<6} {got:<40} {exp:<12} {q[:55]}")

print(f"\n{pass_c}/{len(checks)} PASS, {fail_c} FAIL")
if fails:
    print("\nFailed:")
    for q, e, g in fails:
        print(f"  exp={e}, got={g}: {q}")
