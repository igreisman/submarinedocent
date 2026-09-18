#!/usr/bin/env python3
"""
scripts/compare_gate.py

Measure what the INCLUDE_GENERATED_FAQS gate changed.

Every faq_ chunk title plus a fixed set of golden questions is run through
retrieve() + synthesize_extractive() twice -- once with generated drafts
answerable (INCLUDE_GENERATED_FAQS=1) and once without (=0) -- and the two
answers are compared.

The gate is read once at import (api/main.py), so the two passes run as
separate subprocesses rather than by swapping api.main.FAQ in place.  That
also keeps the memoised BM25 corpus statistics honest: _corpus_stats()
caches document frequency over the FAQ list as it stood on first retrieval,
so mutating it mid-process would score the second pass with the first
pass's IDF table.

Run from the repo root:
    ./.venv/bin/python3 scripts/compare_gate.py
    ./.venv/bin/python3 scripts/compare_gate.py --limit 25 --out /tmp/gate.csv

CONTENT_ROOT picks the corpus; api/main.py reads .env.local, so set it
explicitly to be sure which one you measured.

PREFLIGHT
---------
The two passes are only a prediction about production if the corpus and the
gate they measure are the ones production is running.  On 18 September 2026
they were not: a comparison was run assuming the gate was open, production had
it closed, and the predicted answer for a question was a draft that the closed
gate never lets answer.  The result read as authoritative and was wrong.

So before running anything, this script fetches /health from the deployment
and refuses unless three things line up:

    include_generated_faqs   the gate this deployment runs
    faq_chunks_total         how many chunks are in its corpus
    faq_chunks               how many of those can answer

A mismatch means the prediction does not describe production, and the run
stops.  --force overrides and stamps every line of output as unverified.
Override the target with SUBDOCENT_BASE_URL, or skip the check entirely with
--no-preflight when you are deliberately measuring something local.
"""

import argparse
import collections
import csv
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED_PREFIXES = ("der_", "pam_", "fix_")
DEFAULT_BASE_URL = "https://submarinedocent.org"

# No golden-question set existed in the repo when this was written.  These 20
# are drawn from the _test/test_batch*_eval.py probe batches, which are the
# project's de-facto regression questions, chosen to cover the subject areas
# where generated drafts actually compete with curated entries: crew life,
# daily operations, torpedoes, and boat systems.  Override with --questions
# FILE (one question per line) once a real golden set exists.
GOLDEN_QUESTIONS = [
    "What did the captain do during a depth charge attack?",
    "How did the crew communicate with each other inside the submarine?",
    "What did crew members wear on a submarine?",
    "What was the significance of being qualified in submarines?",
    "How did the crew handle a torpedo that malfunctioned?",
    "What was a ballast tank on a submarine?",
    "How did submarines navigate at night on the surface?",
    "What were battle stations on a submarine?",
    "What was the role of the pharmacists mate on a submarine?",
    "How did the crew maintain the diesel engines?",
    "Could submarines communicate with each other while submerged?",
    "How did submarines avoid enemy minefields?",
    "What was a fleet boat?",
    "What happened if a crew member died while on patrol?",
    "What was hot bunking on a submarine?",
    "How did the crew sleep on a submarine?",
    "What did the crew eat on a submarine?",
    "How deep could a WWII submarine dive?",
    "What were the problems with US torpedoes?",
    "How many men were in a submarine crew?",
]


# ---------------------------------------------------------------------------
# Worker: one pass, one value of the gate.  Prints JSON on stdout.
# ---------------------------------------------------------------------------
def apply_faq_path(m, faq_path):
    """Point api.main at a different FAQ file, after import.

    FAQ_PATH is derived at import from CORPORA_DIR plus a fixed filename, and
    no environment variable names an arbitrary file, so the override cannot
    happen at import without editing api/main.py.  Re-running the loader here
    is equivalent as long as nothing has been retrieved yet: FAQ_ALL and FAQ
    are rebuilt, and the memoised BM25 statistics are dropped so document
    frequency and mean chunk length are recomputed over the new corpus on the
    next retrieval.  Leaving them cached would score this pass with the IDF
    table of the corpus that was loaded at import.
    """
    if not faq_path:
        return
    resolved = os.path.abspath(faq_path)
    if not os.path.exists(resolved):
        sys.exit(f"--faq-path not found: {resolved}")
    m.FAQ_PATH = resolved
    m.FAQ_ALL = m.load_jsonl(resolved)
    m.FAQ = m._retrievable_faq(m.FAQ_ALL)
    m._avg_chunk_tokens = None
    m._doc_freq = None
    m._doc_count = 0


def run_pass(questions, faq_path=None):
    sys.path.insert(0, REPO)
    from api import main as m

    apply_faq_path(m, faq_path)

    gate = os.getenv("INCLUDE_GENERATED_FAQS", "0")
    # Printed by each pass so the override is visible, not assumed.
    print(f"  [pass INCLUDE_GENERATED_FAQS={gate}] FAQ_PATH = {m.FAQ_PATH}",
          file=sys.stderr)
    print(f"  [pass INCLUDE_GENERATED_FAQS={gate}] chunks: "
          f"{len(m.FAQ_ALL)} in file, {len(m.FAQ)} answerable", file=sys.stderr)

    out = []
    for q in questions:
        hits = m.retrieve(question_text=q, compartment_id="",
                          playhead_time_ms=0, top_k=8)
        if not hits:
            out.append({"q": q, "faq_id": "", "score": "", "answer": ""})
            continue
        resp = m.synthesize_extractive(question_text=q, hits=hits)
        faq_id = resp.get("faq_id") or ""
        # Prefer the score of the chunk that actually supplied the answer;
        # the "why"-question rebuild inside synthesize_extractive can cite a
        # chunk other than hits[0].
        score = hits[0][0]
        for s, ch, _src in hits:
            if ch.get("chunk_id") == faq_id:
                score = s
                break
        out.append({
            "q": q,
            "faq_id": faq_id,
            "top_id": hits[0][1].get("chunk_id") or "",
            "score": round(float(score), 4),
            "answer": (resp.get("answer_short") or "").strip(),
        })
    print("@@JSON@@" + json.dumps({
        "corpus_dir": m.CORPORA_DIR,
        "faq_path": m.FAQ_PATH,
        "faq_answerable": len(m.FAQ),
        "faq_total": len(getattr(m, "FAQ_ALL", m.FAQ)),
        "rows": out,
    }))


def spawn(questions, include_generated, faq_path=None):
    env = dict(os.environ)
    env["INCLUDE_GENERATED_FAQS"] = "1" if include_generated else "0"
    env["COMPARE_GATE_WORKER"] = "1"
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__)],
        input=json.dumps({"questions": questions, "faq_path": faq_path}),
        capture_output=True, text=True, env=env,
    )
    for line in proc.stderr.splitlines():
        if line.startswith("  [pass "):
            print(line)
    if proc.returncode != 0:
        sys.exit(f"worker failed (INCLUDE_GENERATED_FAQS="
                 f"{env['INCLUDE_GENERATED_FAQS']}):\n{proc.stderr[-2000:]}")
    for line in proc.stdout.splitlines():
        if line.startswith("@@JSON@@"):
            return json.loads(line[len("@@JSON@@"):])
    sys.exit("worker produced no result")


# ---------------------------------------------------------------------------
# Preflight: does this run describe the deployment, or something else?
# ---------------------------------------------------------------------------
def fetch_health(base_url):
    """The deployment's own /health, or a string explaining why not."""
    url = base_url.rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            if r.status != 200:
                return f"{url} returned HTTP {r.status}"
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return f"{url} returned HTTP {e.code}"
    except Exception as e:                      # DNS, TLS, timeout, bad JSON
        return f"{url} unreachable: {type(e).__name__}: {e}"


def infer_gate(health, answerable, total):
    """Gate state for a deployment too old to report it.

    Pre-18-Sep-2026 builds expose only the answerable count, so the gate has to
    be inferred by comparing it against the corpus -- which is sound only when
    the corpus measured here is the corpus running there.  That is the
    assumption that produced the wrong prediction in the first place, so this
    returns None rather than guess when the counts do not settle it.
    """
    live = health.get("faq_chunks")
    if live is None:
        return None
    if live == total and total != answerable:
        return True                              # everything answers: gate open
    if live == answerable and total != answerable:
        return False                             # only faq_/fix_: gate closed
    return None


def preflight(base_url, local_gate, answerable, total, force):
    """Refuse to predict for a deployment this run does not match."""
    print(f"preflight        : {base_url}")
    health = fetch_health(base_url)

    problems = []
    if isinstance(health, str):
        problems.append(health)
        live_gate = live_total = live_answerable = None
    else:
        live_gate = health.get("include_generated_faqs")
        live_total = health.get("faq_chunks_total")
        live_answerable = health.get("faq_chunks")

        if live_gate is None:
            live_gate = infer_gate(health, answerable, total)
            if live_gate is None:
                problems.append(
                    "this deployment does not report include_generated_faqs and "
                    "its faq_chunks does not settle the gate by inference")
            else:
                print(f"  gate           : {live_gate} (inferred; deployment "
                      f"predates the include_generated_faqs field)")
        else:
            print(f"  gate           : INCLUDE_GENERATED_FAQS="
                  f"{'1' if live_gate else '0'}")

        if live_total is None:
            problems.append(
                "this deployment does not report faq_chunks_total, so the "
                "corpus measured here cannot be matched against the live one")
        else:
            print(f"  corpus         : {live_answerable} answerable of {live_total}")
            if live_total != total or live_answerable != answerable:
                problems.append(
                    f"corpus mismatch: measuring {answerable} answerable of "
                    f"{total}, deployment serves {live_answerable} of {live_total}")

    print(f"  measuring here : {answerable} answerable of {total}")

    if not problems:
        # Both passes run regardless; naming which one is production is the
        # whole point, because that is the baseline any prediction is against.
        production = "INCLUDE_GENERATED_FAQS=1" if live_gate else "INCLUDE_GENERATED_FAQS=0"
        print(f"  OK             : production runs {production}; "
              f"the other pass is the counterfactual\n")
        return live_gate, False

    print()
    for p in problems:
        print(f"  MISMATCH       : {p}")
    if not force:
        print("\nRefusing to run. A comparison measured against a different "
              "corpus or gate\nis not a prediction about this deployment -- it "
              "reads as one and is wrong.\n"
              "Re-run with --force to proceed anyway, or --no-preflight to skip "
              "this check.")
        sys.exit(2)
    print("\n  *** --force: results below are NOT verified against the "
          "deployment ***\n")
    return live_gate, True


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="gate_comparison.csv")
    ap.add_argument("--faq-path", help="FAQ corpus file to measure instead of "
                                       "the one CONTENT_ROOT resolves to; "
                                       "applied inside both passes")
    ap.add_argument("--questions", help="file of extra questions, one per line "
                                        "(replaces the built-in golden set)")
    ap.add_argument("--limit", type=int, help="only the first N questions "
                                              "(for a quick check)")
    ap.add_argument("--titles-only", action="store_true",
                    help="skip the golden questions")
    ap.add_argument("--base-url", default=os.getenv("SUBDOCENT_BASE_URL",
                                                    DEFAULT_BASE_URL),
                    help="deployment to check this run against "
                         "(default: $SUBDOCENT_BASE_URL or %(default)s)")
    ap.add_argument("--force", action="store_true",
                    help="run even when the corpus or gate does not match the "
                         "deployment; output is stamped unverified")
    ap.add_argument("--no-preflight", action="store_true",
                    help="skip the deployment check entirely (for a "
                         "deliberately local measurement)")
    args = ap.parse_args()

    sys.path.insert(0, REPO)
    from api import main as m

    if args.faq_path:
        resolved_faq = os.path.abspath(args.faq_path)
        if not os.path.exists(resolved_faq):
            sys.exit(f"--faq-path not found: {resolved_faq}")
        faq_all = m.load_jsonl(resolved_faq)
    else:
        resolved_faq = getattr(m, "FAQ_PATH", "")
        faq_all = getattr(m, "FAQ_ALL", m.FAQ)
    titles = [(e.get("title") or "").strip() for e in faq_all
              if (e.get("chunk_id") or "").startswith("faq_")]
    titles = [t for t in titles if t]

    golden = []
    if not args.titles_only:
        if args.questions:
            with open(args.questions, encoding="utf-8") as f:
                golden = [ln.strip() for ln in f if ln.strip()]
        else:
            golden = list(GOLDEN_QUESTIONS)

    questions = titles + golden
    if args.limit:
        questions = questions[: args.limit]

    generated_present = sum(
        1 for e in faq_all
        if (e.get("chunk_id") or "").startswith(GENERATED_PREFIXES))
    print(f"corpus dir       : {m.CORPORA_DIR}")
    print(f"faq corpus       : {resolved_faq}"
          f"{'  (--faq-path override)' if args.faq_path else ''}")
    print(f"faq_ titles      : {len(titles)}")
    print(f"golden questions : {len(golden)}")
    print(f"questions to run : {len(questions)}  (x2 passes)")
    print(f"generated drafts : {generated_present}")
    if not generated_present:
        print("  WARNING: no der_/pam_/fix_ chunks in this corpus; "
              "both passes will be identical.")
    print()

    answerable = sum(1 for e in faq_all
                     if (e.get("chunk_id") or "").startswith(("faq_", "fix_")))
    forced = False
    if args.no_preflight:
        print("preflight        : SKIPPED (--no-preflight); this run is not "
              "checked against any deployment\n")
        forced = True
    else:
        _live_gate, forced = preflight(args.base_url, None, answerable,
                                       len(faq_all), args.force)

    print("running pass 1/2: INCLUDE_GENERATED_FAQS=1 ...")
    with_gen = spawn(questions, True, args.faq_path)
    print("running pass 2/2: INCLUDE_GENERATED_FAQS=0 ...")
    without_gen = spawn(questions, False, args.faq_path)

    # Both passes must have measured the file the parent listed titles from.
    for label, res in (("with", with_gen), ("without", without_gen)):
        if os.path.abspath(res.get("faq_path", "")) != os.path.abspath(resolved_faq):
            sys.exit(f"pass '{label}' used {res.get('faq_path')}, "
                     f"expected {resolved_faq}")

    by_q_with = {r["q"]: r for r in with_gen["rows"]}
    by_q_without = {r["q"]: r for r in without_gen["rows"]}

    rows = []
    changed = 0
    displaced = collections.Counter()
    for q in questions:
        a, b = by_q_with.get(q, {}), by_q_without.get(q, {})
        ans_changed = (a.get("answer") or "") != (b.get("answer") or "")
        if ans_changed:
            changed += 1
        # A generated chunk was displaced when it answered this question with
        # the gate open and no longer does with it closed.
        fid_with = a.get("faq_id") or ""
        if fid_with.startswith(GENERATED_PREFIXES) and fid_with != (b.get("faq_id") or ""):
            displaced[fid_with] += 1
        rows.append({
            "question": q,
            "faq_id_with": fid_with,
            "faq_id_without": b.get("faq_id") or "",
            "score_with": a.get("score", ""),
            "score_without": b.get("score", ""),
            "answer_changed": "y" if ans_changed else "",
        })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["question", "faq_id_with", "faq_id_without",
                                          "score_with", "score_without", "answer_changed"])
        w.writeheader()
        w.writerows(rows)

    pct = (100.0 * changed / len(questions)) if questions else 0.0
    print(f"\nanswerable chunks: {with_gen['faq_answerable']} with gate open, "
          f"{without_gen['faq_answerable']} with it closed "
          f"(corpus holds {with_gen['faq_total']})")
    print(f"questions whose answer changed: {changed} of {len(questions)} ({pct:.1f}%)")
    print(f"rows written: {len(rows)} -> {args.out}")

    if displaced:
        print(f"\ngenerated chunks displaced ({len(displaced)} distinct), "
              f"by questions they were top hit for:")
        for cid, n in displaced.most_common():
            title = next((e.get("title", "") for e in faq_all
                          if e.get("chunk_id") == cid), "")
            print(f"  {n:4d}  {cid:10s} {title[:66]}")
    else:
        print("\nno generated chunk answered any question with the gate open.")

    if forced:
        print("\n" + "*" * 72)
        print("UNVERIFIED: this run was not matched against a deployment.")
        print("Do not cite these figures as a prediction about production.")
        print("*" * 72)


if __name__ == "__main__":
    if os.getenv("COMPARE_GATE_WORKER") == "1":
        payload = json.loads(sys.stdin.read())
        run_pass(payload["questions"], payload.get("faq_path"))
    else:
        main()
