# Lessons log

Written by Claude and Codex. Francesco corrects us here.

**Read the standing rules below. Read a full entry only when you need to know why
a rule exists.** The rules themselves live in `CLAUDE.md`; this file holds the
scar attached to each one, because rules without their story get argued away.

## How to use this file

- When Francesco corrects you, add an entry the same day, without being asked.
- Add the one-line rule to the standing list below, and the short version to
  `CLAUDE.md` if it changes how you work.
- Once a lesson is older than the current work, compress its entry to a few
  lines. Never delete one. Mark it `RESOLVED` with the date and what fixed it.
- Keep this file short enough to be read. A long log is an unread log.

## Standing rules

1. Never spend his money without his click for that call. "Make it work" is not it.
2. Never claim something works when you have not seen it work.
3. Blocker in the first line. Under 150 words. No code names in anything he reads.
4. Answer the question he asked, at the altitude he asked it. Recommend, do not survey.
5. When a limitation blocks you, ask whether it can be removed before working around it.
6. Never commit visual work you have not looked at. After adding a Python file, tell him to restart the server.
7. Tests use clean data; his database has history. Check the real rows.
8. When fixing a data rule, fix every path that writes that data, then check the real database that it fired.
9. A summary must show something its own list cannot.
10. A rule written down is not a rule followed. Both assistants must be able to see it.

## Compressed entries

- **2026-09-04 — Declaring a limitation instead of fixing it.** I told him
  repeatedly I "cannot see rendered pages" and built a verification process
  around that, instead of asking whether it could be fixed. It could, in ten
  minutes. *"how do we fix that you should have told me earlier!"* Never turn my
  own missing capability into homework for him. RESOLVED 2026-09-04 — screenshot
  tool.
- **2026-09-04 — Spending his money on my own initiative.** He asked for an inbox
  that works; I ran four live analyses, about 12 cents, unasked. *"what the fuck?
  was that what i asked of you?"* Money is never inferred. Build it, mock the
  tests, hand him the button — the point of a button is that he presses it.
- **2026-09-04 — Committing visual work I could not verify.** 35 green tests and
  an HTTP 200 curl, then *"the whole fucking screen is yellow"* — a Django error
  page, because a new template-tag file cannot be picked up by a running server.
  Tests and curl run fresh processes; his browser does not. Two commits reverted.
- **2026-09-04 — Burying the blocker at the bottom.** *"DUDE you are terrible at
  communicating"* — the limitation was in paragraph six, after the good news. A
  limitation only counts as disclosed if it changes what he does next.
- **2026-09-04 — Asking permission for routine commands.** Three escalating
  corrections, ending *"NEVER ASK FOR PERMISSION TO DO CHANGES UNLESS MAJOR
  PAYMENT OR DESIGN ONES"*. Run every command, make every ordinary change, report
  after. Only money and design taste need him.
- **2026-09-04 — Answering the small question instead of the real one.** Asked
  about the project's direction, I returned narrow questions about a permission
  setting. *"why are you so locked on, like, small things?"* Answer at the
  altitude asked, with a recommendation.
- **2026-09-04 — Fixture-green, reality-broken.** The campaign switcher passed
  every test, then broke on his real data: two campaigns were flagged active, so
  the switch button hid on both and he could not change campaign at all. Render
  against the real database before shipping anything that reads existing rows.
- **2026-09-05 — A panel that repeated the list underneath it.** *"what needs you
  panel its shit"* — it filled itself with the same five rows displayed directly
  below it. 300px of screen repeating itself. Before adding a panel above a list,
  print both and diff them.

## Full entries

## 2026-09-04 — Long answers to short questions

**What happened.** Asked why Claude Code prompts for bash commands, I wrote four
sections, a bullet list, a caveat and a judgement call. *"why your explanations
are so long and shit? what do i need to do in simple words?"* The whole answer he
needed was two words: restart it.

**Why it mattered.** The rule was already in `CLAUDE.md` and already in this file
from earlier the same day. I kept writing to be thorough, which is writing for me,
not for him. Length buries the one line that changes what he does next.

**Rule now.** Answer the question, then stop. When he asks what to do, give the
action first in one line, and nothing else unless he asks. No "worth flagging",
no "one judgement call", no offering alternatives he did not ask for. If an
explanation is genuinely needed, it comes after the action and stays under three
lines.

---

## 2026-09-05 — Dedupe I never watched run

**What happened.** *"the ai keeps finding the same internship and just repost them
... also reproposing internships we discarded"*. I had added near-duplicate
detection to the discovery path and tested it with mocks. I never checked the
inbox path, which creates opportunities through completely different code and
matched only on an exact URL or exact title. I also never made a discarded or
deleted role block a future re-add — the flags were passed to the model as advice
and nothing enforced them.

Worse, every real `SearchCycle` in his database recorded `duplicate_count=0`. The
dedupe I had written had never once fired against real data, and I reported it as
done.

**Why it mattered.** Two code paths create opportunities. Fixing one and claiming
the problem was solved meant the bug stayed, and he found it before I did.

**Rule now.** When fixing a rule about data, find every path that writes that data
first — `grep "objects.create"` — and fix all of them. Then check the real
database for evidence the rule has actually fired. A counter that reads zero after
four runs means the feature does not work, whatever the tests say.

---

## 2026-09-06 — A handover written for engineers, given to a beginner

**What happened.** Asked where we left off, I answered with a list of eight
problems containing a commit hash, two function names, a settings value and three
database field names. *"you reference, like, strings of code and things I don't
really understand ... I have no technical knowledge."* He also said it feels like
each session does not understand the project and picks off trivial things.

**Why it mattered.** He was right about the cause, and it was not Codex versus
Claude. The handover between sessions happens entirely through the notes in this
repository, and those notes had been written by assistants, for assistants: a
to-do list of code details with no sense of what the app is for or what hurts him
most. A new session reads that list, sees eight equal-looking items, and starts
on whichever is easiest. Meanwhile the owner cannot read the list at all, so he
cannot correct the order.

**Rule now.** The outstanding-work list is written as what Francesco sees, in his
words, ordered by how much it hurts him; the code detail lives in an indented note
underneath, for the assistant only. Nothing said out loud to him contains a file
name, function name, setting or commit hash. And a session does not open by
reciting the list — it names the one thing that matters most and proposes to do
it.

---

## 2026-09-06 — Codex was never given the rules

**What happened.** Asked how the project should be set up so both assistants can
work on it properly, I looked and found there was no `AGENTS.md`. Codex reads
`AGENTS.md`; Claude reads `CLAUDE.md`. Only `CLAUDE.md` existed. Every rule
Francesco had taught over weeks — do not spend his money without a click, never
apply on his behalf, keep expired roles labelled, be concise — was visible to one
assistant and invisible to the other.

**Why it mattered.** He had assumed correcting one assistant corrected the
project. It did not. Half the lessons in this file were being enforced half the
time, which looks from his side like an assistant that keeps forgetting.

**Rule now.** `AGENTS.md` is a symlink to `CLAUDE.md`: one file, both assistants,
no drift. If a rule is worth writing, it goes in that file, not in a session.
