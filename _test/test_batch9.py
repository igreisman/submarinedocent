"""Batch 9 regression tests — pam_156 through pam_176."""
import json, ssl, urllib.request, time, sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

TESTS = [
    ("What was the control room used for on a submarine?",              "pam_156"),
    ("What did the forward torpedo room look like?",                    "pam_157"),
    ("How did the crew dispose of garbage on a submarine?",             "pam_158"),
    ("What happened to enemy survivors after a submarine attack?",      "pam_159"),
    ("How did submarines handle fires or flooding emergencies?",        "pam_160"),
    ("What was a periscope feather?",                                   "pam_161"),
    ("How did the crew avoid boredom on a long patrol?",                "pam_162"),
    ("What was the role of the TDC operator?",                          "pam_163"),
    ("What happened if a submarine ran aground?",                       "pam_164"),
    ("What did a Japanese convoy look like?",                           "pam_165"),
    ("How did the Pampanito earn her battle stars?",                    "pam_166"),
    ("What was the flying bridge on a submarine?",                      "pam_167"),
    ("How deep could the Pampanito dive?",                              "pam_168"),
    ("What was the magnetic exploder problem with US torpedoes?",       "pam_169"),
    ("Who was the most successful US submarine commander of WWII?",     "pam_170"),
    ("How did the crew celebrate after a successful attack?",           "pam_171"),
    ("What did submariners do when they returned to port after a patrol?", "pam_172"),
    ("Why were submarines called the Silent Service?",                  "pam_173"),
    ("How did submarine construction change during the war?",           "pam_174"),
    ("What was a snorkel on a submarine?",                              "pam_175"),
    ("What was periscope depth on a submarine?",                        "pam_176"),
    # existing FAQs that should remain stable
    ("What was a hydrophone on a submarine?",       "pam_010"),
    ("What were wolfpack tactics?",                 "pam_131"),
    ("What was a crash dive?",                      "pam_060"),
    ("How many US submarines were lost in WWII?",   "pam_061"),
    ("How did radar work on a submarine?",          "pam_110"),
    ("How were torpedo reloads handled at sea?",    "pam_006"),
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
for _ in range(15):
    try:
        with urllib.request.urlopen(
            urllib.request.Request("https://localhost:8443/health"),
            context=ctx, timeout=3
        ) as r:
            d = json.loads(r.read())
            if d.get("faq_chunks", 0) >= 400:
                print(f"Server up ({d['faq_chunks']} FAQs)\n")
                break
    except Exception:
        pass
    time.sleep(2)
else:
    print("ERROR: server not ready"); sys.exit(1)

passed = failed = 0
failures = []

for question, expected in TESTS:
    try:
        resp = ask(question)
        got = resp.get("faq_id") or "(tour)"
        ok = (expected is None) or (got == expected)
        tag = "PASS" if ok else "FAIL"
        print(f"{tag} [{got:30s}] {question[:65]}")
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append((question, expected, got))
    except Exception as e:
        failed += 1
        failures.append((question, expected, f"ERROR: {e}"))
        print(f"ERR  {question[:65]} — {e}")

print(f"\n{'='*60}")
print(f"Batch 9: {passed}/{passed+failed} passed")
if failures:
    print("\nFailed:")
    for q, exp, got in failures:
        print(f"  expected={exp} got={got}: {q[:70]}")
    sys.exit(1)
