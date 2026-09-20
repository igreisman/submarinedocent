# Maintaining

Tasks for whoever runs the deployment. Contributors do not need any of this;
see [CONTRIBUTING.md](../CONTRIBUTING.md).

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
