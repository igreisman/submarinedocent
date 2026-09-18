# Architecture

How a question becomes an answer, and where the content lives. Short on
purpose; `api/main.py` is the whole application and is the authority.

## The shape of it

One FastAPI process serves the API and the static pages. There is no database,
no vector store, no background worker and no queue. Content is JSONL files on
disk. State that changes — corpus edits, feedback — is written back to those
files atomically.

    browser ──► /ask ──► retrieve() ──► synthesize_extractive() ──► answer
                            │
                            └── BM25 over the corpora in memory

## Corpora

Every corpus is one JSON object per line, loaded into memory at startup. See
[../corpora/README.md](../corpora/README.md) for what each one is and who owns
it.

Four are searched when a question arrives, weighted so that answers written for
this project outrank reference material:

| Corpus | Weight | Why |
|---|---:|---|
| `dieselsubs_faq_corpus.jsonl` | 1.2 | The source of truth. Written to answer questions. |
| `dieselsubs_shorts_corpus.jsonl` | 0.8 | Short answers. Supplement the FAQ, never displace it. |
| `dieselsubs_fleetsub_manual.jsonl` | 0.5 | 2,189 chunks of 1946 Navy engineering prose. Answers only what nothing else can. |
| `dieselsubs_sub_losses_wwii.jsonl` | 0.5 | Primary-source government text, not written as answers. |

The manual is an order of magnitude larger than everything else, which is why
it is weighted so far down: left level, its sheer volume would win questions
the FAQ answers better.

The rest — glossary, categories, lost boats, incidents, museums, Medal of Honor
citations, the video catalogue — back their own pages and APIs rather than
`/ask`.

## Retrieval

`overlap_score()` is BM25 with IDF. `k1` is 1.5. `b` is 0.3, tunable by
`BM25_B` and deliberately low: chunk length here reflects the kind of content,
not verbosity, so penalising long chunks would penalise the manual for being a
manual.

Document frequency and mean chunk length are computed once, on the first
retrieval, and anchored to the corpora written for this project — in practice
the FAQ and shorts. (The loop also covers a tour corpus that is not distributed
here, so that list is empty.) The manual and the losses report are scored
*against* those statistics rather than folded into them — adding 2,189 chunks of Navy
prose to the IDF table shifts the frequency of common terms enough to change
answers that have nothing to do with it. Measured, that cost a point of
self-retrieval even with the manual's own weight set to zero.

`retrieve()` scores every corpus, multiplies by the weight above, and returns
the top 8 as `(score, chunk, source_id)`. A query matching an FAQ title word
for word gets `EXACT_TITLE_BOOST`, 20.0 by default, which is large enough to
make an exact title match effectively unbeatable.

`synthesize_extractive()` then builds the answer out of the retrieved records.
It does not generate text. `USE_LLM=true` switches to synthesis; the deployed
site does not use it.

## The review gate

FAQ records carry a prefix that says how far through review they are:

- `faq_` — reviewed. Answerable.
- `fix_` — a correction to a reviewed record. Answerable.
- `der_`, `pam_` — generated drafts. **Not** answerable.

Two lists exist for this. `FAQ_ALL` is the whole file and is what the admin
tools and every write path see. `FAQ` is the answerable subset and is what
retrieval sees. `_retrievable_faq()` is the filter between them, and
`INCLUDE_GENERATED_FAQS=1` disables it.

This matters because it is easy to measure the wrong one. `/health` reports
both counts and the gate state — `faq_chunks`, `faq_chunks_total`,
`include_generated_faqs` — so a tool can tell which world it is looking at.
`scripts/compare_gate.py` reads all three and refuses to run against a corpus
or gate that does not match the deployment it claims to describe.

A draft becomes answerable through `accept_faq()`, which renames it to the next
free `faq_NNN`. Acceptance rewrites `source` to `accepted_from_<old_id>`, so
the original value is copied to `original_source` first — without that, a
promoted draft stops declaring where it came from, and a provenance audit that
filters on `source` silently spares exactly the records that are live.

## Editable content

`_editable_corpus_path()` decides where a corpus is read and written.

On Render a persistent disk is mounted at `/data`. The first boot copies the
bundled `corpora/` file across, and from then on `/data` is authoritative, so a
curator's edits survive a redeploy that rebuilds the container from git. Locally
there is no disk and everything resolves to `corpora/`.

The consequence worth knowing: **editing a file in `corpora/` and pushing does
not change production.** The bundled copy is a seed, not the live content. Ship
a corpus change through the admin API or by copying onto `/data`.

## Admin

Basic Auth in middleware, not per route, so a new `/admin/` route or
`web/edit_*.html` page is protected the moment it exists. Credentials come from
the environment; there is no default and no built-in password. Unset, the
protected surface returns `503` — off, not merely locked — and CI asserts that
on every push.

Failed authentications are throttled: five per address per fifteen minutes,
plus a global backstop of fifty in the same window. The address is the one the
trusted proxy appends, chosen by walking `X-Forwarded-For` from the right —
never the leftmost value, which the client writes and could otherwise use to
pick its own throttle key.

`GET /admin/backup` returns the whole `/data` directory as a tarball, which is
why the password is the only thing standing between a guesser and the entire
dataset, and why the throttle exists.

## Video

No video is stored in this repository. `corpora/videos.jsonl` holds catalogue
records — title, description, category, tags, ordering, and a URL pointing at
YouTube or at the project's own object storage.

Each record carries `rights_status` and `rights_note`. `_rights_cleared()` is
the single gate deciding whether an asset reaches a visitor; anything not
cleared is simply absent, and the surrounding answer renders unchanged because
answer text is written to stand on its own. Admin endpoints read raw records
instead, so a curator can see and fix what the public pages are withholding.

`RIGHTS_STRICT=true` makes an unrecorded status mean "not cleared" rather than
"not reviewed". Check `GET /admin/rights` before setting it.
