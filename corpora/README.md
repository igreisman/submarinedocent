# corpora/

The content the docent answers from. One JSONL file per corpus, one record per
line.

**Licensing is per file, not per directory.** `LICENSE-CONTENT` grants CC BY 4.0
over the text written for this project. Anything marked public domain below is
outside that grant because it needs no grant from us. Photographs and video are
excluded from it entirely — see the photographs section here and in
`LICENSE-CONTENT`.

## Inventory

Counts are the records in this repository, refreshed from the live site on
18 September 2026.

**Only reviewed records ship.** The FAQ corpus on the live site carries 487
records; 167 of them are unreviewed generated drafts, and those stay on the
server. What is published here is the 320 records that are actually allowed to
answer a visitor — every `faq_` and `fix_` record and nothing else. A draft has
not been checked by anyone, so publishing one would put our name on text no
human has read. See Withheld below.

| File | Records | Origin | Licensing |
|---|---:|---|---|
| `dieselsubs_faq_corpus.jsonl` | 385 | Written by Irving Greisman, some of it first published on dieselsubs.com — his own site. | **CC BY 4.0** |
| `dieselsubs_shorts_corpus.jsonl` | 31 | Written by Irving Greisman, derived from the DieselSubs YouTube channel — his own channel. | **CC BY 4.0** |
| `dieselsubs_faq_categories.jsonl` | 13 | Category names, from the dieselsubs.com FAQ structure — his own site. | **CC BY 4.0** |
| `eternal_patrol.jsonl` | 65 | Lost-boat records written by Irving Greisman. **References photographs** in `web/images/extracted/`. | Text **CC BY 4.0**. **Photographs are not** — see below. |
| `incidents.jsonl` | 16 | Written by Irving Greisman. | **CC BY 4.0** |
| `museums.jsonl`, `museum_pages.jsonl` | 20, 2 | Museum directory and per-museum pages written by Irving Greisman. **References a header photograph** in `museum_uploads/`. | Text **CC BY 4.0**. **The photograph is not**, see below. |
| `videos.jsonl` | 108 | Catalogue records — titles, descriptions, categories, tags, ordering — written by Irving Greisman. They point at video hosted elsewhere, mostly YouTube. | Records **CC BY 4.0**. **The video is not** — see below. |
| `dieselsubs_glossary.jsonl` | 204 | Written by Dwight Naset. | **CC BY 4.0**, released by him 18 September 2026. Credit Dwight Naset, not submarinedocent.org. |
| `dieselsubs_fleetsub_manual.jsonl` | 2,189 | *Fleet Type Submarine* manual series, US Navy, 1946. | **Public domain** — US federal government work. Not ours to license. |
| `dieselsubs_sub_losses_wwii.jsonl` | 9 | *United States Submarine Losses, World War II*, US Navy, 1946. | **Public domain** — US federal government work. Not ours to license. |
| `moh_recipients.jsonl` | 8 | Medal of Honor citations, US Navy. | **Public domain** — US federal government work. Not ours to license. |

Three groups, and the difference matters:

1. **Irving's own work** — the FAQ, shorts, categories, lost boats, incidents,
   museums and video catalogue. dieselsubs.com and the DieselSubs YouTube
   channel are his own properties, so material derived from them is his to
   license. CC BY 4.0, attributed as described in `LICENSE-CONTENT`.

2. **Dwight Naset's glossary**, released by him under CC BY 4.0 by email on
   18 September 2026. It is his work, not this project's, so attribution goes
   to him by name rather than to submarinedocent.org.

3. **United States Government works** — the two 1946 Navy publications and the
   Medal of Honor citations. These are in the public domain in the United
   States as works of the federal government. We neither grant nor can grant
   rights in them; they are here as primary sources.

Two record types carry something the CC BY grant does not reach, and the table
above flags both:

- `eternal_patrol.jsonl` **text** is CC BY. The **photographs** it references
  are not — see the next section.
- `videos.jsonl` **records** are CC BY. The **video** they point at is not.
  No video is distributed in this repository, each record carries its own
  `rights_status` and `rights_note`, and nothing here grants any rights in the
  linked material.

## Photographs

Photographs referenced from these records are of mixed provenance, are used
with credit for non-commercial educational purposes, and are **excluded from
the CC BY grant, which covers text only.**

`eternal_patrol.jsonl` carries a credit beside every image:

```
photo_boat          → photo_boat_credit
photo_captain       → photo_captain_credit
image1 … image4     → image1_credit … image4_credit
```

Credits render beneath the image on the lost-boat page. The default,
`"Photo via NavSource Naval History"`, records the route an image reached us by
— NavSource aggregates from many contributors — and is **not** a claim about who
holds the rights. Where a contributor is identified, name them in the credit
field instead; the admin editor accepts these fields.

A museum's header photograph is carried in `museums.jsonl` in three fields:

```
header_image_url → header_image_credit, header_image_alt
```

The file itself sits in `museum_uploads/<page id>/`, and the same file is
recorded as an attachment on that museum's page in `museum_pages.jsonl`. The
attachment record is what ties the image to its provenance. A record with a
`header_image_url` and no `header_image_credit` is rejected on write and renders
nothing, so a header photograph cannot reach a visitor uncredited.

The one shipped here, `museum_uploads/1/1_NH-79761-USS-Cod.jpg`, is a U.S. Navy
photograph held by the Naval History and Heritage Command as NH 79761, courtesy
of D.M. McPherson. As a work of the United States government it is in the public
domain, which is why it can ship at all. Most photographs this project uses are
not, which is why they carry per-image credits and sit outside the grant.

## Withheld

The live site holds two things this repository does not:

- **167 generated FAQ drafts** (`der_` prefixed). Unreviewed. They cannot answer
  a visitor on the live site either — `_retrievable_faq()` filters them out —
  and they are not published here for the same reason: nobody has read them.
  They become publishable one at a time, by review, which renames them `faq_`.
- **Visitor feedback and submitted questions.** Personal data. Never published.

One field was cleared on the way out rather than copied: a museum record on the
live site still carries `tour_url: /web/pampanito.html`, a page that was
withdrawn and returns 404. It is `null` here.

## Records removed

Records derived from a third party's website were removed on 17 and 18
September 2026. See [`scripts/remove_by_source.py`](../scripts/remove_by_source.py).
