# Security Policy

## Supported Development Line

Security fixes should target the current main branch and the currently deployed configuration.

## Reporting A Vulnerability

Do not open a public issue for a suspected security problem.

Report it privately, by either route:

1. **Email dieselsubs1945@gmail.com.** This is the project address and it is
   monitored. Put "security" in the subject.
2. **GitHub private security advisory** — the "Report a vulnerability" button
   on the Security tab, which opens a thread visible only to the maintainer.

You will get an acknowledgement. This is a one-maintainer project, so expect a
human reply in days rather than hours, and no bounty — there is no budget for
one. Credit in the fix commit is offered gladly if you want it.

Please include:

- a description of the issue
- affected routes, pages, or files
- reproduction steps
- impact assessment
- any suggested mitigation, if known

## Sensitive Areas In This Project

Changes in these areas should be reviewed carefully:

- `/admin/*` routes, and `/admin/backup` above all
- `/feedback/list`
- admin-facing web pages in `web/`, which is every `web/edit_*.html`
- auth, throttling and redirect middleware in `api/main.py`
- startup scripts and environment-variable handling

## Current Security Expectations

- admin routes must remain protected server-side, in middleware rather than per route
- with no credentials configured, the protected surface returns `503` — off, not merely locked
- secrets must be supplied via environment variables; there are no compiled-in defaults and none may be added
- failed authentications must stay throttled, and the throttle must key on the address the trusted proxy appends, never on the leftmost `X-Forwarded-For` value, which the client controls
- local certificates and feedback exports must stay out of version control

`GET /admin/backup` returns the entire `/data` directory as a tarball. The admin
password is the only thing between a guesser and the whole dataset, which is why
the throttle and the `503`-when-unconfigured behaviour are both load-bearing
rather than defensive extras.
