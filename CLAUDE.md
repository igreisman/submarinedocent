# CLAUDE.md

submarinedocent.org: an independent educational site about the United States submarine force in WWII, with an Ask the Docent tool that answers from a curated corpus. FastAPI backend, static HTML front end, BM25 retrieval over JSONL files. No embeddings, no vector store, no LLM in the default path.

Maintainer: Irving Greisman. Public repo: github.com/igreisman/submarinedocent. Internal planning lives in `docs/internal/`, a separate private repo nested here and ignored by this one.

## Start of every session

1. List `docs/internal/inbox/`. Material from Irving's other assistant arrives there, and it is the half of the exchange that is easy to miss: nothing announces a new file. Read anything you have not already acted on before starting work that it might cover, and record in the relevant plan that you have. A set of video descriptions sat unread there for a day while the same descriptions were written from scratch.
2. Read `docs/internal/open-source-release-plan.md` for the release work and its Decisions log, and `docs/internal/video-integration-plan.md` if the task touches video.
3. Read the plan's "Current standing" before assuming anything about the code or corpus.
4. Say which track you are picking up.

## Before you act

- State a design decision and the alternative you rejected before proceeding, then append it to the plan's Decisions log with the date. Never delete a decision; supersede it.
- If a step needs a name, date, page number, citation, or count you do not have, stop and ask. Do not fill the gap with a plausible value. Names of real people go in public files only when Irving supplies them.
- If an instruction contains a placeholder like `[list]`, stop and ask. Do not guess what was meant.
- Report sizes as tracked bytes or disk bytes, and say which.

## Retrieval and corpus

- The FAQ corpus is the source of truth. A wrong answer is almost always a wrong or missing record, not a retrieval bug.
- Any change to scoring, `retrieve()`, `add_hits`, or the gate moves answers site-wide. Measure with the self-retrieval sweep (every `faq_` title plus the golden questions) before and after, and show the full diff including regressions, before committing.
- `compare_gate.py` refuses to run against a corpus or gate setting that does not match production. Do not bypass with `--force` unless Irving says so.
- Only `faq_` and `fix_` records answer visitors. `der_` records are unreviewed and stay behind the gate until a person accepts them. `pam_` is extinct: the last of those records was removed on 17 September 2026 and the prefix should not come back. Per-museum draft prefixes are intended but do not exist yet; they belong to the museum-pages plan.
- `accept_faq()` must preserve `original_source`. Provenance is what a rights question reads.
- Production corpora live on `/data`, not in git. `corpora/` is the seed. Run `make refresh-seed` before any release or announcement; it stages, never commits.
- After any bulk admin-API change, pull a fresh backup and diff it against the previous one. A 200 response is not proof the record is intact.

## Git and publishing

- This repo is public. Never amend a pushed commit, never force-push, never rewrite history. Every change is an ordinary commit.
- One commit per logical change. Show the diff before pushing when the change touches licensing files, the README, `CONTRIBUTING.md`, or anything visitor-facing.
- Never commit: `.env*` except `.env.example`, anything under `/data` patterns, backups, `corpora_local/`, Finder duplicates (`* copy*`), review CSVs, design sources, or `docs/internal/`.
- Nothing under `docs/internal/` ships. The public `docs/` holds three files: `architecture.md`, `maintaining.md`, and `images/ask-the-docent.png`.

## Identity and rights

- USS Pampanito is subject matter, not the site's identity. It appears in content as one boat among many. It must not appear in the **site identity**: the site name, the tagline, the repo description, the Ask the Docent prompts, or the domain. Page titles for boat content are content, not identity: `pampanito-hub.html`, `pampanito-patrols.html` and `pampanito-patrol-1.html` name the boat and that is correct.
- Content derived from the San Francisco Maritime National Park Association's tour or website was removed on 17 and 18 September 2026 and must not be reintroduced. Anything sourced from maritime.org or the audio tour is out.
- Photographs and third-party video are used with credit and are excluded from the CC BY grant. Never relicense them. Every video record carries `rights_status`; the `_rights_cleared()` gate decides what is shown.
- When a rights holder grants permission, record it on the record with the date, the person, and the condition, and update `corpora/README.md` if the licensing statement changes.

## Reporting

End every substantive report with a section headed **For Irving's other assistant** containing three lines: what changed, what needs a decision, what you recommend. Irving relays that block; write it so it stands alone.

Irving relaying it is the point, not a missing feature. Files come from that assistant through `docs/internal/inbox/`, because files are safer written than pasted. Nothing goes back except through him, because these reports end in decisions and the decisions are his. Two assistants exchanging files directly would be faster and would have shipped a fabricated surname, a wrong museum name and a wrong crew count, each of which a human in the middle caught first. Do not propose an outbox; the question is settled, and the reasoning is in the museum-pages plan under 24 September 2026.

## Lessons

Each of these cost real work. They are here so the next person does not pay again.

- Shell `grep` here is `ugrep --ignore-files` and honours `.gitignore`, so a scrub can come back falsely clean. Use a gitignore-blind walk for any secrets or provenance check.
- `make refresh-seed` leaves its changes staged, and a later `git commit` naming other paths still picks them up. Commit with explicit paths after a refresh.
- A rule written for a corpus that no longer ships can still fire. `remove_compartment_noise` stripped the only token from "What is in the after battery?" and the site answered "I don't have that detail" while holding the record.
- Two records sharing a title present as a retrieval bug and are a content bug. The self-retrieval test fails on duplicates for that reason.
- Check the HTTP status before parsing a response. A 502 during a Render restart parses as an empty answer and reads as a failing test.
- `PUT /admin/videos/{id}` scrapes YouTube when the payload carries no metadata field, so send title, description, channel_name, channel_url and thumbnail_url or expect a fill.
- A guarantee that lives only in one tree is not a guarantee. `original_source` was written in the release clone, never ported, and was silently lost when that clone became the working repo. If it matters, it needs a test in CI.

## Working style

- Irving prefers one strong recommendation over a list of options, and direct language over hedging.
- No em dashes in email drafts or in **new** visitor-facing prose. Existing files keep theirs; do not run a cleanup pass.
- When you find a problem outside the task, report it and continue; do not fix it silently unless leaving it would break the current task.
- When a comparison or check turns out to have used the wrong setting, say so plainly and rerun. Corrections to your own earlier reports go in the record, not quietly into the file.
