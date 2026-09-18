"""Batch 10 regression tests — pam_177–pam_197 plus stable legacy."""
import requests, urllib3
urllib3.disable_warnings()

BASE = "https://localhost:8443"

TESTS = [
    # pam_177 — OOD / officer of the deck
    ("What was the officer of the deck responsible for on a submarine?",        "pam_177"),
    ("What did the OOD do while the submarine was underway?",                   "pam_177"),
    # pam_179 — crew training / submarine school
    ("How were new submarine crew members trained and certified for duty?",     "pam_179"),
    # pam_180 — sound-powered telephone
    ("What was a sound-powered telephone on a submarine?",                      "pam_180"),
    # pam_181 — identify ships at night
    ("How did submarines identify enemy ships at night?",                       "pam_181"),
    # pam_182 — after torpedo room
    ("What was the after torpedo room used for?",                               "pam_182"),
    # pam_183 — Navy selects submariners
    ("How did the Navy select men for submarine duty?",                         "pam_183"),
    # pam_184 — crew if boat sunk
    ("What happened to the crew of a submarine that was sunk?",                 "pam_184"),
    # pam_185 — night surface attacks
    ("How did submarines attack targets at night on the surface?",              "pam_185"),
    ("What was a night surface attack?",                                        "pam_185"),
    # pam_186 — lookout duties
    ("What did the lookouts on a submarine watch for?",                         "pam_186"),
    ("How were lookout watch sectors organized and assigned on a submarine?",   "pam_186"),
    # pam_187 — refueled in Pacific
    ("How were submarines refueled in the Pacific?",                            "pam_187"),
    ("What advance bases did US submarines use for refueling in the western Pacific?", "pam_187"),
    # pam_188 — angle on the bow
    ("What was the angle on the bow?",                                          "pam_188"),
    # pam_189 — radio communication with Pearl Harbor
    ("How did submarines communicate with Pearl Harbor during a patrol?",       "pam_189"),
    ("How did submarines receive radio intelligence from Pearl Harbor while on patrol?", "pam_189"),
    # pam_190 — forward engine room
    ("What was the forward engine room on a submarine?",                        "pam_190"),
    # pam_191 — navigate to patrol area
    ("How did submarines navigate to their patrol areas from Pearl Harbor?",    "pam_191"),
    ("How did submarine navigators use celestial observations to determine their position?", "pam_191"),
    # pam_192 — when to surface decision
    ("How did submarine captains decide when to surface?",                      "pam_192"),
    ("What timing considerations guided a submarine captain's decision to surface?", "pam_192"),
    # pam_193 — escape trunk
    ("What was the escape trunk on a submarine?",                               "pam_193"),
    ("How could a sailor escape a sunken submarine?",                           "pam_193"),
    # pam_194 — sonar operators tracking
    ("How did sonar operators track enemy ships?",                              "pam_194"),
    ("What did sonar operators listen for when a submarine was hunting?",       "pam_194"),
    # pam_195 — chief of the boat
    ("What was the role of the chief of the boat?",                             "pam_195"),
    ("How was the COB involved in managing a submarine's trim?",                "pam_195"),
    # pam_196 — torpedo spreads / fan shots
    ("How did torpedo spreads work?",                                           "pam_196"),
    ("What was a torpedo spread?",                                              "pam_196"),
    # pam_197 — avoid submarine collision / friendly fire
    ("How did submarines avoid colliding with each other?",                     "pam_197"),
    ("How did geographic patrol zones prevent submarines from attacking each other?", "pam_197"),
    # legacy stable
    ("How did submarines navigate without GPS?",                                "pam_009"),
    ("What was a submarine tender?",                                            "pam_089"),
    ("How many torpedoes did the Pampanito carry?",                             "pam_067"),
    ("What was the test depth of the Pampanito?",                               "pam_168"),
    ("What was a snorkel on a submarine?",                                      "pam_175"),
    ("How did sonar work on a WWII submarine?",                                 "pam_010"),
    ("How deep could a WWII submarine dive?",                                   "pam_025"),
]

pass_count = 0
fail_count = 0
for question, expected in TESTS:
    resp = requests.post(f"{BASE}/ask", json={"question_text": question, "lang": "en"}, verify=False)
    got = resp.json().get("faq_id", "(none)")
    status = "PASS" if got == expected else "FAIL"
    if status == "PASS":
        pass_count += 1
    else:
        fail_count += 1
    print(f"{status}  expected={expected}  got={got}  | {question}")

total = pass_count + fail_count
print(f"\n{pass_count}/{total} passed")
