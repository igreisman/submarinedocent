"""Batch 11 evaluation — 30 new questions, check what the system returns."""
import requests, urllib3, json
urllib3.disable_warnings()

BASE = "https://localhost:8443"

QUESTIONS = [
    # Q01 — maneuvering room
    "What was the maneuvering room on a submarine?",
    # Q02 — periscope attack procedure
    "What happened step by step when a submarine made a periscope attack?",
    # Q03 — torpedo reload procedure
    "How did the torpedo room crew reload a torpedo tube after firing?",
    # Q04 — deck gun
    "Did the Pampanito have a deck gun and how was it used?",
    # Q05 — after engine room
    "What was the after engine room on a submarine?",
    # Q06 — trim dive / trim check
    "What was a trim dive on a submarine?",
    # Q07 — diving planes (control surfaces)
    "What were the diving planes on a submarine?",
    # Q08 — radar use for navigation and attack
    "How did submarines use radar during World War II?",
    # Q09 — executive officer role (XO)
    "What was the role of the executive officer on a submarine?",
    # Q10 — dealing with tropical heat
    "How did submarine crews cope with the heat in the tropics?",
    # Q11 — what made a good submarine captain
    "What qualities made a good submarine commander?",
    # Q12 — homecoming after patrol
    "What happened when a submarine returned to port after a war patrol?",
    # Q13 — depth charge attack experience
    "What was it like to be inside a submarine during a depth charge attack?",
    # Q14 — periscope exposure time / feather
    "How long could a submarine expose its periscope without being detected?",
    # Q15 — forward torpedo room
    "What was the forward torpedo room like on the Pampanito?",
    # Q16 — patrol area assignment / zones
    "How were submarine patrol areas assigned during World War II?",
    # Q17 — war patrol duration / length
    "How long did a typical World War II submarine war patrol last?",
    # Q18 — food quality / provisioning
    "What kind of food did submarine crews eat on patrol?",
    # Q19 — commissioning / launching ceremony
    "What was the commissioning ceremony for a submarine?",
    # Q20 — contact report / reporting sightings
    "How did submarines report enemy contacts to headquarters?",
    # Q21 — maneuvering to avoid escort
    "How did submarines evade destroyers and escort ships?",
    # Q22 — air patrols / airplanes as submarine threat
    "Why were aircraft such a serious threat to submarines?",
    # Q23 — wolfpack tactics
    "What were wolfpack tactics and did the US Navy use them?",
    # Q24 — torpedo data computer operation
    "How did the torpedo data computer work?",
    # Q25 — submarine vs submarine
    "Did US submarines ever engage enemy submarines?",
    # Q26 — magnetic exploder / contact exploder
    "What was the difference between a magnetic exploder and a contact exploder?",
    # Q27 — control room layout
    "What was in the control room of the Pampanito?",
    # Q28 — ship's log / record keeping
    "What records did submarines keep during a patrol?",
    # Q29 — crew morale / recreation
    "How did submarine crews maintain morale on long patrols?",
    # Q30 — Japanese anti-submarine warfare
    "How effective was Japanese anti-submarine warfare against US submarines?",
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
