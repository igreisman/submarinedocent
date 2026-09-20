# Contributing

## Correcting an answer

**This is the contribution this project most wants**, and it needs no Python.

The site answers from a curated corpus, so a wrong answer is almost always a
wrong or missing record — not a bug in retrieval. Fixing the record fixes the
answer.

### Where the answers live

`corpora/dieselsubs_faq_corpus.jsonl`, one JSON object per line. A reviewed
record looks like this:

```json
{
  "chunk_id": "faq_591",
  "title": "Is a submarine a boat or a ship?",
  "text": "<p>Most often the difference between boats and ships is based on size...</p>",
  "category": "Hull and Compartments",
  "source": "dieselsubs.com FAQ",
  "display_citation": "DieselSubs FAQ — Is a submarine a boat or a ship?",
  "topic_tags": ["submarine", "boat"],
  "era": "ww2"
}
```

`title` is what a visitor's question is matched against, and an exact title
match is weighted heavily — so the title should read like the question someone
would actually ask, not like a heading. `text` is HTML. `source` says where the
material came from and is not decoration: it is what a provenance audit reads.

### The review gate

The `chunk_id` prefix says how far through review a record is, and retrieval
only sees two of them:

| Prefix | Meaning | Can it answer? |
|---|---|---|
| `faq_` | Reviewed | **Yes** |
| `fix_` | A correction to a reviewed record | **Yes** |
| `der_`, `pam_` | Generated draft, not reviewed | **No** |

A draft sits in the file without ever reaching a visitor until someone accepts
it, at which point it is renamed to the next free `faq_NNN`. This is why adding
a record is safe and why nothing you add is live until it has been read by a
person.

**Name new records `fix_` or `faq_`** — a `der_` record will be committed and
then never answer anything.

### What a good correction looks like

- **It cites a source.** This is the one hard requirement. A correction without
  a citation cannot be reviewed and will not be merged. Published books, Navy
  documents, official histories and museum records carry weight. Forum posts,
  undated web pages and "I served on one" do not — not because they are wrong,
  but because a reader cannot check them.
- **It is specific.** "The torpedo section is wrong" is a bug report. "The Mark
  14's magnetic exploder was deactivated by order in June 1943, not 1942" is a
  correction.
- **It says what was wrong.** The pull request should explain the error, not
  just present the replacement. Whoever reviews it needs to know what to check.
- **It stays in one voice.** Answers are written plainly, for a visitor with no
  background. Avoid jargon the record does not itself explain.
- **It leaves the title alone** unless the title is the problem. Changing a
  title changes what questions the record answers.

### Checking your change

Retrieval is lexical, so a new record can quietly lose to an existing one. Run
the question against a local instance before opening the pull request:

```bash
./start_https.sh                        # one shell
.venv/bin/python _test/spot_check.py    # another
```

If you changed anything about retrieval itself rather than a record, say so
explicitly — the scoring constants were tuned against those scripts and the
totals are the regression signal.

### If you would rather not open a pull request

Open an issue with the question you asked, the answer you got, and what it
should have said. That is genuinely useful: the question is the evidence for
what needs writing. Or email dieselsubs1945@gmail.com.

## Scope

This repository mixes application code with historical content and deployment-specific material. Keep changes narrowly scoped and call out whether your change affects:

- application code
- historical corpora or editorial content
- deployment configuration
- admin workflow pages

## Before You Start

1. Read [README.md](README.md)
2. Read [docs/architecture.md](docs/architecture.md) if you are touching retrieval
3. Read [corpora/README.md](corpora/README.md) if you are touching content
4. Use `.env.local` for local configuration
5. Do not commit secrets, local certs, or feedback exports

## Development Setup

```bash
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

For local HTTPS testing, use:

```bash
./start_https.sh
```

## Contribution Guidelines

- Prefer minimal, focused changes
- Preserve existing public behavior unless the change intentionally updates it
- Add or update documentation when configuration or workflow changes
- Do not introduce hardcoded secrets, local IPs, or environment-specific assumptions
- Treat admin and feedback surfaces as sensitive features and keep server-side protection in place

## Content Changes

If you change corpora, text, or media references:

- identify the source of the material
- confirm that redistribution and modification are allowed
- note any provenance or licensing constraints in the pull request

## Refreshing the corpus seed

**Run `make refresh-seed` before any release or announcement.**

`corpora/` in this repository is a *seed*, not the live content. In production
the editable corpora live on a persistent disk, seeded from `corpora/` on first
boot and authoritative from then on — so a curator's edit on the live site
never reaches this repository by itself. The two drift apart silently and
continuously, and the gap only shows up when someone reads the published corpus
and finds it stale.

```bash
export SUBDOCENT_BASE_URL=https://submarinedocent.org
export ADMIN_USERNAME=... ADMIN_PASSWORD=...

make refresh-seed ARGS=--dry-run   # look first
make refresh-seed                  # write and stage
```

It pulls the deployment's own corpora, prints a per-file diff, validates the
result, and **stages the changes without committing**, so a person reads the
diff before it becomes history. It never commits and never pushes.
Credentials come from the environment only.

Two rules are baked in and are the reason this is a script rather than a copy:

- **Only reviewed FAQ records are published.** `der_` and `pam_` chunks are
  unreviewed drafts. They cannot answer a visitor on the live site either, and
  publishing one would put the project's name on text nobody has read. The
  refresh keeps `faq_` and `fix_` and drops the rest.
- **The FAQ corpus and the categories file move together.** FAQ records name
  their category as a string, so refreshing one without the other leaves every
  record pointing at a category that does not exist, and an empty dashboard for
  the first person to clone the repository. The script refreshes both and then
  checks that every referenced category is defined.

It refuses to run when `corpora/` already has uncommitted changes, because a
refresh tangled with hand edits produces a diff nobody can review — you can no
longer tell which change came from the live site and which came from a person.

Anything the live disk holds that this repository does not ship is listed and
ignored rather than silently imported.

## Testing

At minimum, contributors should:

- verify the app starts locally
- verify public pages still load
- verify protected admin routes remain protected
- run any targeted test scripts relevant to the changed area

## Pull Requests

Include:

- a short summary of what changed
- why the change was needed
- any environment variables or deployment settings affected
- any follow-up work that remains
