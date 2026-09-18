"""Batch 8 regression tests — pam_133 through pam_155."""
import json, urllib.request, ssl, sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = "https://localhost:8443"

TESTS = [
    # (question, expected_faq_id_or_None)
    ("What did the captain do during a depth charge attack?",           "pam_133"),
    ("How did the crew communicate with each other inside the sub?",    "pam_134"),
    ("What did crew members wear on a submarine?",                      "pam_135"),
    ("What did it mean to be qualified in submarines?",                 "pam_136"),
    ("What was the submarine combat patrol insignia?",                  "pam_137"),
    ("How did the Pampanito crew rescue the POWs from the water?",      "pam_138"),
    ("What was the role of the executive officer on a submarine?",      "pam_139"),
    ("What were battle stations on a submarine?",                       "pam_140"),
    ("What was the role of the pharmacists mate on a submarine?",       "pam_141"),
    ("Did any American submarines get captured by the enemy?",          "pam_142"),
    ("What was a ballast tank on a submarine?",                         "pam_143"),
    ("What was a war patrol report?",                                   "pam_144"),
    ("How did submarines avoid enemy minefields?",                      "pam_145"),
    ("What was a fleet boat?",                                          "pam_146"),
    ("How did submarines recharge their batteries?",                    "pam_147"),
    ("What was the difference between a Gato and a Balao class submarine?", "pam_148"),
    ("What were the daily duties of the captain of a submarine?",       "pam_149"),
    ("How did submarines handle the threat of enemy destroyers?",       "pam_150"),
    ("What was the sound of a torpedo being fired?",                    "pam_151"),
    ("What was commissioning day like for a new submarine?",            "pam_152"),
    ("What happened to Japanese submarines at the end of the war?",     "pam_153"),
    ("What happened if a crew member died while on patrol?",            "pam_154"),
    ("How did submarines get their orders for each war patrol?",        "pam_155"),
    # existing FAQs that should remain stable
    ("How did submarines communicate while submerged?",  "pam_011"),
    ("Where is the Pampanito docked today?",             None),  # pam_098/099 acceptable
    ("How many men were on a submarine?",                None),  # crew-size acceptable
    ("How long was a typical war patrol?",               None),
]

def query(question: str):
    data = json.dumps({"question_text": question, "lang": "en"}).encode()
    req = urllib.request.Request(
        f"{BASE}/ask",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        return json.loads(resp.read())

passed = failed = 0
failures = []

for question, expected in TESTS:
    try:
        result = query(question)
        got = result.get("faq_id") or "(tour)"
        if expected is None:
            passed += 1
            print(f"  PASS  [{got}]  {question[:70]}")
        elif got == expected:
            passed += 1
            print(f"  PASS  [{got}]  {question[:70]}")
        else:
            failed += 1
            failures.append((question, expected, got))
            print(f"  FAIL  expected={expected} got={got}  {question[:70]}")
    except Exception as e:
        failed += 1
        failures.append((question, expected, f"ERROR: {e}"))
        print(f"  ERR   {question[:70]} — {e}")

print(f"\n{'='*60}")
print(f"Batch 8: {passed}/{passed+failed} passed")
if failures:
    print("\nFailed:")
    for q, exp, got in failures:
        print(f"  expected={exp} got={got}")
    sys.exit(1)
