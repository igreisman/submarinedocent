"""
Quick local scoring debug — mimics main.py retrieve() to show top-5 hits
for each failing query.
"""
import json, re, sys
from pathlib import Path

CORPUS_DIR = Path("corpora")

def load(p):
    return [json.loads(l) for l in open(p) if l.strip()]

TOUR = load(CORPUS_DIR / "pampanito_tour_corpus.jsonl")
FAQ  = load(CORPUS_DIR / "dieselsubs_faq_corpus.jsonl")

STOPWORDS = {
    "the","a","an","what","were","was","is","are","of","on","in",
    "to","and","for","some","between","did","do","does","you",
    "it","that","this","with","as","at","by","from","about",
    "whats","what's","difference","please","tell","me",
    "any","there","than","other",
    "where","how","when","who","which","whose","whom",
    "after","forward",
    "submarine","boat","sub",
    "got","get","gets","gotten","happened","happen",
    "someone","something","somebody","anyone","anything",
    "people","person","things","thing",
    "could","would","should","had","have","has","if","its","been",
    "world","war","ii",
}

QUERY_SYNONYMS = {
    "men":["crew","sailors","crewmen","enlisted","personnel","complement"],
    "served":["crew","crewmen","complement","enlisted","assigned"],
    "crew":["men","sailors","crewmen","complement","personnel","enlisted"],
    "torpedo":["torpedoes","fired","launched","shot","warhead"],
    "torpedoes":["torpedo","fired","launched","shot","warhead"],
    "toilet":["head","restroom","bathroom","latrine"],
    "submarines":["sailors","crewmen","crew","enlisted","men","personnel"],
}

def tokenize(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split()
            if t not in STOPWORDS and (len(t) > 2 or (len(t)==2 and t.isdigit()))]

def expand(tokens):
    out = list(tokens)
    seen = set(tokens)
    for t in tokens:
        for s in QUERY_SYNONYMS.get(t, []):
            if s not in seen:
                out.append(s)
                seen.add(s)
    return out

def overlap(qtoks, text):
    exp = set(expand(qtoks))
    ttoks = set(tokenize(text))
    return len(exp & ttoks)

def score_chunk(ch, qtoks, weight):
    text = ch.get("text","")
    s = overlap(qtoks, text)
    if s <= 0:
        return 0.0, s, 1.0, False
    ew = weight
    bonus_fired = False
    paras = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    if paras and paras[0].rstrip().endswith("?"):
        title_toks = set(tokenize(paras[0]))
        q_set = set(qtoks)
        q_exp_set = set(expand(qtoks))
        matched = len(q_exp_set & title_toks)
        if title_toks:
            coverage = matched / len(title_toks)
        else:
            coverage = 0
        all_q_covered = all(
            t in title_toks or
            any(syn in title_toks for syn in QUERY_SYNONYMS.get(t, []))
            for t in q_set
        )
        if all_q_covered:
            ew = weight * 4.0 * coverage
            bonus_fired = True
        elif matched >= max(1, len(q_set)-1):
            ew = weight * 2.0 * coverage
    # quantity boost
    if re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten"
                 r"|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen"
                 r"|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy"
                 r"|eighty|ninety|hundred|thousand)\b", text, re.I):
        ew *= 1.5
    return s * ew, s, ew, bonus_fired

_CMAP = [
    (re.compile(r"\bconning\s+tower\b", re.I), "conning_tower"),
]

def debug_query(q):
    qtoks = tokenize(q)
    print(f"\n=== {q!r} ===")
    print(f"  q_tokens: {qtoks}")
    named_comp = None
    for pat, cid in _CMAP:
        if pat.search(q):
            named_comp = cid
    if named_comp:
        print(f"  named_compartment: {named_comp}")

    hits = []
    for ch in TOUR:
        s, overlap_n, ew, bonus = score_chunk(ch, qtoks, 3.0)
        if named_comp and ch.get("compartment_id") == named_comp:
            s *= 3.0
            ew *= 3.0
        if s > 0:
            hits.append((s, ch["chunk_id"], "tour", overlap_n, ew, bonus))
    for ch in FAQ:
        s, overlap_n, ew, bonus = score_chunk(ch, qtoks, 1.2)
        if s > 0:
            hits.append((s, ch["chunk_id"], "faq", overlap_n, ew, bonus))

    hits.sort(reverse=True)
    print(f"  {'SCORE':>8} {'ID':<40} {'SRC':<5} {'OVL':>4} {'EW':>6} BONUS")
    for sc, cid, src, ovl, ew, bonus in hits[:6]:
        print(f"  {sc:8.2f} {cid:<40} {src:<5} {ovl:>4} {ew:>6.2f} {'YES' if bonus else ''}")

queries = [
    "What were the biggest dangers for submarine crews?",
    "How many American submarines were lost in WWII?",
    "Did submarines ever rescue people from the water?",
    "Did the Pampanito save POWs?",
]

for q in queries:
    debug_query(q)
