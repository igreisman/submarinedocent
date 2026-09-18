import json, os, ssl, time, urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API = "https://localhost:8443"


def ask(q):
    body = json.dumps({"question_text": q, "compartment_id": ""}).encode()
    req = urllib.request.Request(f"{API}/ask", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        return json.loads(r.read())


for i in range(12):
    try:
        ask("test"); print("UP"); break
    except Exception:
        time.sleep(1)

# Spot check previous batches.
#
# Each entry lists EVERY chunk that genuinely answers the question, not a
# single row id.  The corpus holds several overlapping FAQ entries on the same
# subject (der_008 and pam_066 both explain running on the surface at night),
# so pinning one id made the check fail on a correct answer.
#
# The original expectations were written against pam_* ids that were later
# renamed to fix_*/der_* with the same number.  Ten of eighteen pointed at rows
# that no longer existed, so the check reported failures the app was not
# responsible for.  verify_expectations() below fails loudly if that recurs.
spot_checks = [
    ("How many torpedo reloads does the Pampanito carry?", {"der_067", "fix_006"}),
    ("How could a submarine run underwater without air?", {"der_007", "pam_065"}),
    ("Why did submarines stay on the surface at night?", {"der_008", "pam_066"}),
    ("How did submarines navigate without GPS?", {"der_009"}),
    ("How many ships did the Pampanito sink?", {"der_012", "der_226"}),
    ("When was the Pampanito built?", {"fix_013"}),
    ("What is a depth charge?", {"fix_015"}),
    ("How did the crew breathe underwater?", {"fix_018"}),
    ("How did a torpedo work?", {"pam_019"}),
    ("How did the captain fire torpedoes?", {"pam_021"}),
    ("Where is the Pampanito?", {"pam_022"}),
    ("What class of submarine is the Pampanito?", {"pam_023"}),
    ("What happened to the Pampanito after the war?", {"fix_024"}),
    # der_168 ("How deep could the Pampanito dive?") gives the same 400 ft test
    # depth as pam_025 ("How deep could a WWII submarine dive?") — either is a
    # correct answer to the generic question.
    ("How deep could a submarine dive?", {"pam_025", "der_168"}),
    ("How fast could a submarine go?", {"pam_026"}),
    ("How long did it take to train submarine crews?", {"pam_028"}),
    ("How could submariners escape a sinking submarine?", {"fix_029"}),
    ("Were women on submarines in WWII?", {"pam_031"}),
]


def verify_expectations():
    """Abort if any expected chunk id is absent from the corpus.

    A renamed row silently turns into a permanent FAIL that looks like a
    retrieval bug, which is exactly how the previous ten went unnoticed.
    """
    root = os.environ.get("CONTENT_ROOT", "corpora")
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = root if os.path.isabs(root) else os.path.join(repo, root)
    corpus = os.path.join(path, "dieselsubs_faq_corpus.jsonl")
    if not os.path.exists(corpus):
        raise SystemExit(f"CANNOT VERIFY: corpus not found at {corpus}")
    known = set()
    with open(corpus, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                known.add(json.loads(line).get("chunk_id"))
    expected = {cid for _, ids in spot_checks for cid in ids}
    stale = sorted(expected - known)
    if stale:
        raise SystemExit(
            f"STALE EXPECTATIONS: {len(stale)} chunk id(s) no longer in the corpus: "
            f"{', '.join(stale)}\nUpdate spot_checks above before trusting this run."
        )


verify_expectations()

print(f"\n{'RESULT':<6} {'GOT':<12} {'EXPECTED':<24} QUESTION")
print("-" * 96)
pass_c = fail_c = 0
for q, accepted in spot_checks:
    r = ask(q)
    got = r.get("faq_id") or (r.get("citations") or [{}])[0].get("chunk_id", "??")
    ok = got in accepted
    pass_c += ok
    fail_c += not ok
    exp = "|".join(sorted(accepted))
    print(f"{'PASS' if ok else 'FAIL':<6} {got:<12} {exp:<24} {q[:44]}")

print(f"\n{pass_c}/{len(spot_checks)} PASS, {fail_c} FAIL")
