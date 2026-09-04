# Lessons log

Written by Claude and Codex. Francesco corrects us here.

**Read this file at the start of every session, together with `CLAUDE.md`.**
`CLAUDE.md` holds the rules. This file holds *why* those rules exist — the actual
mistake that caused each one. Rules without their story get argued away; rules
with a scar attached do not.

## How to use this file

- When Francesco corrects you, add an entry the same day. Do not wait to be asked.
- One entry per real mistake. Write what happened, why it mattered, and the rule
  that follows. Be specific and unflattering; a vague entry teaches nothing.
- When a lesson becomes a hard rule, also add the short version to `CLAUDE.md`
  and link back here.
- Never delete an entry. Mark it `RESOLVED` with the date and what fixed it.

---

## 2026-09-04 — Declaring a limitation instead of fixing it

**What happened.** I told Francesco repeatedly that I "cannot see rendered
pages", and built a whole verification rule around that limitation. What I never
did was ask whether the limitation could be removed. It could: a headless browser
and a screenshot script take ten minutes to set up, and I can read PNG files.
Francesco's reaction: *"DUDE what do you mean you can't see rendered pages??? how
do we fix that you should have told me earlier!"*

**Why it mattered.** Two weeks of work were gated behind "Francesco, please go
look at the page for me" — including a change that shipped broken because I
committed visuals I had never seen. The bottleneck was mine and I had normalised
it, turning my own missing capability into homework for the person I work for.

**Rule now.** When a limitation blocks verification, the first move is to ask
whether it can be removed — before designing a process around it. State the
limitation *and* the cost of fixing it, and let Francesco decide. Never quietly
convert a capability gap into manual work for him.

**Status.** RESOLVED 2026-09-04 — see "Taking screenshots" in `CLAUDE.md`.

---

## 2026-09-04 — Committing visual work I could not verify

**What happened.** I replaced the app's icons with an SVG set and restyled the
badges, ran the test suite (35/35 green), curled the page (HTTP 200), and
committed. Francesco opened the app: *"its all fucked"*, *"the whole fucking
screen is yellow"*. The yellow was Django's debug error page.

**Root cause.** I created `tracker/templatetags/icons.py` while his dev server was
already running. Django builds its template-tag registry once, at engine
construction, so a running server never sees a newly created tag library. Every
page raised `TemplateSyntaxError: 'icons' is not a registered tag library`. My
own checks passed because tests and curl each ran in a *fresh* process — the one
environment that could not reproduce his.

**Why it mattered.** Green tests were used as evidence for something they could
not possibly prove. Two commits had to be reverted (`d327198`, `6859116`).

**Rule now.** A passing test proves the code path, not the page. Never commit CSS,
template or layout changes until they have been seen rendered. After adding any
new Python file, say "restart your server" before asking him to look at anything.

---

## 2026-09-04 — Burying the blocker at the bottom

**What happened.** *"DUDE you are terrible at communicating how do i improve
you?"* — I had genuinely mentioned the no-browser limitation, but in paragraph
six of a long report, after the good news. He read the top, trusted it, and
found out the hard way.

**Why it mattered.** A limitation only counts as disclosed if it changes what he
does next. Buried, it is decoration.

**Rule now.** Blocker, limitation or risk in the FIRST line. Under 200 words by
default. Say what you cannot verify *before* doing the work, not after.

---

## 2026-09-04 — Asking permission for routine commands

**What happened.** I kept pausing for approval on ordinary project commands —
`manage.py test`, `makemigrations`, `git status`. Francesco, twice, the second
time in capitals: *"i accept every command cmon"* / *"ALWAYS ALLOW BASH COMMANDS
FROM NOW ON REMEMBER"*.

**Rule now.** Run project commands without asking. This does not touch the
standing safety rules, which are his and stay: never read or print `.env`, never
trigger a paid Robert search without explicit approval, never apply, email or
contact anyone.

---

## 2026-09-04 — Answering the small question instead of the real one

**What happened.** Asked about the overall direction of the project, I came back
with narrow implementation questions about a permission hook. *"why are you so
that locked on, like, small things? I'm asking you about, like, the overarching
things and, like, come up with solution."*

**Why it mattered.** He is a beginner at software and running a job hunt. He needs
the shape of the thing and a recommendation, not a menu of technical options.

**Rule now.** Answer the question actually asked, at the altitude it was asked.
Bring a recommendation, not a survey. Ask only when two readings would lead to
materially different work — and when he says just do it, just do it.

---

## 2026-09-04 — Fixture-green, reality-broken

**What happened.** The campaign switcher passed every test, then failed on his
real database: his legacy data had *two* campaigns flagged active, so the button
condition `{% if not campaign.is_active %}` hid the switch on **both** cards. He
would have been unable to change campaigns at all. Caught only because I rendered
the page against the real database before shipping.

**Rule now.** Tests use clean fixtures; his data has history. Before shipping
anything that reads existing rows, render it against the real database and look
at the actual output.
