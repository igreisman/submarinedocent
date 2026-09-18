"""Batch 12 evaluation — 30 new questions, check what the system returns."""
import requests, urllib3, json
urllib3.disable_warnings()

BASE = "https://localhost:8443"

QUESTIONS = [
    # Q01 — forward torpedo room layout
    "What did the forward torpedo room look like and what equipment was in it?",
    # Q02 — submarine tenders / support vessels
    "What was a submarine tender and what did it provide to submarines?",
    # Q03 — Mark 14 torpedo depth running failures
    "Why did the Mark 14 torpedo run deeper than set and what was done about it?",
    # Q04 — ULTRA intelligence
    "How did ULTRA codebreaking intelligence help US submarines find targets?",
    # Q05 — down the throat / stern shot tactics
    "What was a down-the-throat shot on a submarine?",
    # Q06 — submarine mine avoidance
    "How did submarines avoid mines during their patrols?",
    # Q07 — JANAC / tonnage claims
    "Were the tonnage figures claimed by US submarines accurate?",
    # Q08 — pump room
    "What was the pump room on a submarine?",
    # Q09 — night surface attacks
    "How did submarines attack convoys on the surface at night?",
    # Q10 — hot bunking
    "What was hot bunking on a submarine and why was it necessary?",
    # Q11 — radio room / communications shack
    "What happened in the radio room on a submarine?",
    # Q12 — Pampanito after the war
    "What happened to the USS Pampanito after World War II ended?",
    # Q13 — Japanese merchant shipping losses
    "How much shipping did US submarines sink during World War II?",
    # Q14 — torpedo tube mechanics
    "How did a torpedo tube actually work to launch a torpedo?",
    # Q15 — forward battery compartment / officers quarters
    "What was the forward battery compartment and why did officers sleep there?",
    # Q16 — officer's country / wardroom
    "What was the wardroom on a submarine?",
    # Q17 — Medal of Honor in submarine service
    "Were any submariners awarded the Medal of Honor during World War II?",
    # Q18 — postal mail / letters from home
    "How did submarine crews send and receive mail?",
    # Q19 — gun action / deck gun attacks
    "When did submarines use their deck guns instead of torpedoes?",
    # Q20 — submarine versus surface ship gun fight
    "Did submarines ever fight it out on the surface with enemy ships using guns?",
    # Q21 — conning tower vs control room difference
    "What was the difference between the conning tower and the control room?",
    # Q22 — submarine presidential unit citation
    "What was a Presidential Unit Citation and how did the Pampanito earn one?",
    # Q23 — after battery compartment / enlisted berthing
    "What was the after battery compartment and where did the crew sleep?",
    # Q24 — submarine war patrols in both oceans
    "Did US submarines operate in the Atlantic as well as the Pacific?",
    # Q25 — submarine crew pay / extra pay
    # already covered by pam_018 / faq entries potentially
    "Did submarine sailors get paid more than other sailors?",
    # Q26 — japanese merchant ship types
    "What kinds of ships did US submarines prefer to attack?",
    # Q27 — Pampanito specific patrols / number of ships sunk
    "How many ships did the USS Pampanito sink during the war?",
    # Q28 — what did submarine torpedo room smell like
    "What did the inside of a submarine torpedo room smell like?",
    # Q29 — conning tower periscopes / two scopes
    "Why did submarines have two periscopes?",
    # Q30 — after torpedo room layout
    "What was in the after torpedo room of a fleet submarine?",
]

results = []
for i, q in enumerate(QUESTIONS, 1):
    resp = requests.post(f"{BASE}/ask", json={"question_text": q, "lang": "en"}, verify=False)
    d = resp.json()
    faq_id = d.get("faq_id") or "(tour)"
    ans = (d.get("answer_short") or "")[:120].replace("\n", " ").strip()
    results.append((i, faq_id, q, ans))
    print(f"Q{i:02d}  {faq_id:<20}  {q[:60]}")
    print(f"      {ans[:100]}")

print(f"\nTotal: {len(results)} questions")
