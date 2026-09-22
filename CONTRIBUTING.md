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
  "doc_type": "dieselsubs_faq",
  "title": "Is a submarine a boat or a ship?",
  "text": "<p>Most often the difference between boats and ships is based on size...</p>",
  "category": "Hull and Compartments",
  "source": "dieselsubs.com FAQ",
  "display_citation": "DieselSubs FAQ — Is a submarine a boat or a ship?",
  "slug": "is-a-submarine-a-boat-or-a-ship",
  "topic_tags": ["submarine", "boat"],
  "authority_level": "reference_faq",
  "era": "ww2",
  "platform": ["us_diesel_electric_submarines"]
}
```

`title` is what a visitor's question is matched against, and an exact title
match is weighted heavily — so the title should read like the question someone
would actually ask, not like a heading. `text` is HTML. `source` says where the
material came from and is not decoration: it is what a provenance audit reads.

### Fields with a fixed vocabulary

These take one of a fixed set of values. A value outside the set is not
rejected on write, it just fails quietly later, so copy them exactly.

| Field | Allowed value |
|---|---|
| `doc_type` | `dieselsubs_faq` |
| `authority_level` | `reference_faq` |
| `era` | `ww2` |
| `platform` | `["us_diesel_electric_submarines"]` |

`era` is `ww2` on every record, including ones about a boat's postwar life.
There is no `postwar` value. If one is ever needed it has to be added
deliberately, because nothing filters on `era` today and a second value that
nothing reads is a value nobody maintains.

Do not add `pampanito_specific`. It exists on 28 older records and is set on
no new ones.

### Categories

`category` must match one of these **exactly**, including the spaces after the
full stops in `U. S.` The dashboard groups by this string, so a near miss puts
the record in a category that does not exist and nothing says so.

```
Attacks and Battles, Small and Large
Boat Histories
Crews Aboard U. S. Subs in WW2
Diving and Surfacing
Guns
Hull and Compartments
Japanese Submarines and Torpedoes
Life Aboard U. S. WW2 Subs
Navigation
Operating U. S. Subs in WW2
Pampanito War Patrols
Torpedoes
U. S. WW2 Subs in General
```

`U. S. WW2 Subs in General`, `Operating U. S. Subs in WW2` and `Crews Aboard
U. S. Subs in WW2` are the three that get mistyped, always by dropping the
spaces. `Boat Histories` covers the history of any boat, not one in particular.

The authoritative list is `corpora/dieselsubs_faq_categories.jsonl`. If these
disagree, that file wins and this one is stale.

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
uvicorn api.main:app --port 8000        # one shell
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question_text":"your question here"}'   # another
```

Check that your record is the one that answers, and that it reads well as an
answer rather than as a paragraph of prose. The evaluation scripts in `_test/`
run larger question sets, but they expect a local HTTPS instance and the full
corpora, so they are a maintainer's tool rather than a contributor's.

### If you would rather not open a pull request

Open an issue with the question you asked, the answer you got, and what it
should have said. That is genuinely useful: the question is the evidence for
what needs writing. Or email dieselsubs1945@gmail.com.

## Licensing of contributions

By opening a pull request you agree that your contribution is licensed on the
same terms as the rest of the repository: **code under MIT**, and **content
under CC BY 4.0**. Content means corpus records, documentation and any other
prose.

There is no separate contributor licence agreement to sign, and you keep the
copyright in what you write. This is only so that anyone reusing the project
knows the whole of it carries one set of terms.

Two things follow from that, and they matter more than the paperwork:

- **Do not paste in text you did not write**, from a book, a museum placard,
  another website, or a model's output you have not checked. A citation is how
  a source is credited here; copying its wording is not.
- **Do not contribute material you cannot license**, whatever its quality.
  `corpora/README.md` records where every corpus came from, and a record with
  no answer to "who wrote this" cannot stay.

## What to expect

This is a one-maintainer project. Expect a reply in **days rather than hours**,
and no reply at all during a week when the boat is busy.

A pull request gets merged when three things are true: the change is right, it
cites a source a reader can check, and it is small enough to review in one
sitting. A correction to a single record with a published reference behind it
is the easiest thing to merge here and the most useful thing you can send.

What slows a pull request down: several unrelated changes in one branch, a
rewrite of a record whose title decides which questions it answers, or an
assertion with no source. None of those are refusals, they are just questions
that take a while to work through.

If something is wrong and you would rather not open a pull request at all,
open an issue. A well-described wrong answer is worth more than a fix that
needs unpicking.

## Code changes

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local
SAMPLE_CONTENT_MODE=true uvicorn api.main:app --port 8000
```

Keep changes focused and preserve existing public behaviour unless the change
is deliberately altering it. Do not commit secrets, local certificates or
feedback exports, and do not add environment-specific assumptions such as a
hardcoded address. Admin and feedback surfaces are sensitive; server-side
protection stays in place.

CI boots the app in sample mode on every pull request and checks that the
public endpoints answer and that the admin surface returns `503` while no
credentials are set.

Say in the pull request what changed, why, and whether any environment
variable or deployment setting is affected.

Maintenance tasks, including refreshing the corpus seed from the live site,
are in [docs/maintaining.md](docs/maintaining.md).
