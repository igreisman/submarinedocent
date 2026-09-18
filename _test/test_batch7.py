"""Batch 7 test: 30 questions, check top FAQ returned."""
import json, ssl, urllib.request, time, sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# (question, expected_faq_id)  None = any answer acceptable
TESTS = [
    ("What was the lifeguard mission in WWII?",                                   "pam_113"),
    ("Did the Pampanito participate in rescue operations for downed pilots?",      None),
    ("Did submarines ever lay mines?",                                             "pam_114"),
    ("How did a depth charge attack feel inside a submarine?",                     "pam_115"),
    ("What was hot bunking on a submarine?",                                       "pam_116"),
    ("How did the submarine deck gun work?",                                       "pam_117"),
    ("How did the Pampanito get its name?",                                        "pam_118"),
    ("What was the torpedo data computer?",                                        "faq_983"),
    ("How did submarine crews handle a fire onboard?",                             "pam_119"),
    ("Did WWII American submarines have a snorkel?",                               "pam_120"),
    ("How did submarine crews celebrate after sinking a ship?",                    None),
    ("What was the role of submarines at the Battle of Midway?",                   "pam_121"),
    ("What was radio direction finding and how did it threaten submarines?",       "pam_122"),
    ("How did the crew deal with claustrophobia?",                                 "pam_123"),
    ("What was the galley like on a submarine?",                                   "pam_124"),
    ("How did submarine crews get fresh water?",                                   "pam_125"),
    ("How many war patrols did the Pampanito complete?",                           "faq_1012"),
    ("Was the Pampanito ever close to being sunk?",                                "pam_126"),
    ("What is the National Historic Landmark designation of the Pampanito?",       "faq_1012"),
    ("How did a submarine attack a convoy?",                                       "pam_127"),
    ("What was a ping in submarine terms?",                                        None),
    ("How did the crew handle seasickness on a submarine?",                        "pam_128"),
    ("Did the Pampanito ever sink a Japanese warship?",                            "pam_129"),
    ("What were wolfpack tactics in WWII submarines?",                             "pam_131"),
    ("How many torpedoes did the Pampanito fire during the war?",                  None),
    ("What is the difference between a trim dive and a normal dive?",              "faq_839"),
    ("What was a submarine escape trunk?",                                         None),
    ("Were submarines used to land spies or special forces?",                      "pam_132"),
    ("How did submarines handle the threat of aircraft?",                          "pam_130"),
    ("What was the role of the executive officer on a submarine?",                 None),
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
            if d.get("faq_chunks", 0) >= 364:
                print(f"Server up ({d['faq_chunks']} FAQs)\n")
                break
    except Exception:
        pass
    time.sleep(2)
else:
    print("ERROR: server not ready"); sys.exit(1)

passed = failed = 0
failures = []

for q, exp in TESTS:
    try:
        resp = ask(q)
        got = resp.get("faq_id")
        ok = (exp is None) or (got == exp)
        tag = "PASS" if ok else "FAIL"
        display_id = got or "(tour)"
        print(f"{tag} [{display_id:25s}] {q[:65]}")
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append((exp, got, q))
    except Exception as e:
        print(f"ERR  {q[:65]}: {e}")
        failed += 1

print(f"\n{passed}/{passed+failed} PASS, {failed} FAIL")
if failures:
    print("\nFailed:")
    for exp, got, q in failures:
        print(f"  exp={exp}, got={got}: {q[:70]}")
