"""
Regression tests for Batch 12 FAQs (pam_211–pam_226).
Run with: .venv/bin/python3 test_batch12.py
"""
import requests, json, time, urllib3
urllib3.disable_warnings()

BASE = "https://localhost:8443/ask"
PASS = "✓"; FAIL = "✗"

tests = [
    # (description, query, expected_faq_id)
    ("Submarine tenders",               "What was a submarine tender and what services did it provide?",               "pam_211"),
    ("Submarine tenders (alt)",         "How did submarine tenders support the US submarine campaign in the Pacific?",  "pam_211"),
    ("Mark 14 depth problem",           "Why did the Mark 14 torpedo have a depth running failure?",              "pam_212"),
    ("Mark 14 depth problem (alt)",     "What caused the Mark 14 torpedo to run deeper than set?",               "pam_212"),
    ("ULTRA intelligence",              "How did ULTRA codebreaking help submarines find convoy routes?",            "pam_213"),
    ("ULTRA intelligence (alt)",        "What was the JN-25 cipher and how did ULTRA codebreaking work?",            "pam_213"),
    ("Down-the-throat shot",            "What was a down-the-throat torpedo shot?",                          "pam_214"),
    ("Mine threats",                    "How did submarines avoid mines in the Pacific?",                     "pam_215"),
    ("JANAC tonnage accuracy",          "Were submarine sinking claims accurate?",                            "pam_216"),
    ("JANAC (alt)",                     "What did JANAC say about submarine tonnage claims?",                 "pam_216"),
    ("Strategic results",               "What was the strategic impact of the US submarine campaign?",       "pam_217"),
    ("Torpedo tube mechanics",          "How was a torpedo loaded into its tube and fired?",                      "pam_218"),
    ("Torpedo tube mechanics (alt)",    "What was the sequence for flooding and firing a torpedo tube?",           "pam_218"),
    ("Officers country",                "What was in the forward battery compartment officers country?",      "pam_219"),
    ("Medal of Honor submariners",      "Which submarine crew members received the Medal of Honor?",          "pam_220"),
    ("Medal of Honor (alt)",            "Who was Commander Gilmore and why did he receive the Medal of Honor?",  "pam_220"),
    ("Submarine mail",                  "How did V-mail work and how did families write to submariners?",         "pam_221"),
    ("Mail (alt)",                      "How did submarine mail get delivered and what was V-mail?",              "pam_221"),
    ("Deck guns vs torpedoes",          "When did submarines use deck guns instead of torpedoes to conserve them?",  "pam_222"),
    ("Deck guns (alt)",                 "Why would a submarine use its deck gun to attack a surface target?",         "pam_222"),
    ("Conning tower vs control room",   "What is the difference between the conning tower and control room?", "pam_223"),
    ("Conning tower vs control room (alt)", "How is the conning tower different from the control room?",     "pam_223"),
    ("Presidential Unit Citation",      "Did Pampanito receive the Presidential Unit Citation?",              "pam_224"),
    ("Two periscopes",                  "Why did submarines have two periscopes?",                            "pam_225"),
    ("Two periscopes (alt)",            "What were the two periscopes and what was each one used for?",         "pam_225"),
    ("Pampanito war record",            "How many ships did Pampanito sink during the war?",                  "pam_226"),
    ("Pampanito war record (alt)",      "What was Pampanito's war record?",                                   "pam_226"),
]

passed = failed = 0
for desc, query, expected in tests:
    try:
        r = requests.post(BASE, json={"question_text": query, "lang": "en"},
                          verify=False, timeout=10)
        data = r.json()
        got = data.get("faq_id") or "—"
        ok = got == expected
        if ok:
            passed += 1
            print(f"  {PASS} {desc}")
        else:
            failed += 1
            print(f"  {FAIL} {desc}")
            print(f"       Q: {query}")
            print(f"       expected={expected}  got={got}")
            ans = data.get('answer', '')[:120]
            print(f"       ans: {ans}")
    except Exception as e:
        failed += 1
        print(f"  {FAIL} {desc}: ERROR {e}")
    time.sleep(0.1)

total = passed + failed
print(f"\n{'='*50}")
print(f"Batch 12: {passed}/{total} passed")
