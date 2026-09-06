# Project handoff

`AGENTS.md` and `CLAUDE.md` are the same file, so Codex and Claude get identical
rules and neither drifts. Read this, then `README.md` for what the app does and
`PROJECT_BRIEF.md` for what the search is for. Open `LESSONS.md` only when a rule
here needs its story; the standing rules at the top of that file are the summary.

Francesco is not an engineer. He cannot review your code, so he can only judge
your work by using the app and by what you tell him. An unverified claim of
success is worse than saying you are stuck.

## Never

- Never apply, email, contact or submit anything on his behalf.
- Never read, print or commit `.env`. The OpenAI key lives there.
- Never invent a candidate fact or a job fact. Robert cites its sources.
- Never blur verified facts into assumptions or AI conclusions. Store the source
  and the date for every job, company and contact fact.
- Never collect leaked, hidden or private contact details. Public professional
  contact information only.

## Ask him for two things only

1. **Spending money** — a Robert search, research run or inbox analysis. His
   click. Never infer it from "make it work", "fix it", "go" or "just do
   everything": those authorise building and mocked tests, never a real paid
   call. Build the feature, test it with mocks, then hand him the button.
2. **Design direction** — a visual or product taste decision that is his.

Everything else — commands, refactors, migrations, fixes, tests, commits — just
do, then report what you did.

## How to talk to him

- Blocker, limitation or risk in the FIRST line. Never bury it.
- Under 150 words unless he asks for more.
- Say what you cannot verify BEFORE doing the work, not after.
- No code in anything you say to him: no file names, function names, settings,
  commit hashes or field names. Name what he sees on screen and what it does
  wrong. Code detail belongs in this file and in commit messages.
- Never open with a list of problems. Name the one that hurts most and propose it.
- Explain software simply. He is a beginner.

## Judgement the code cannot make

- Do not require an employer to call a role a "graduation" or "thesis"
  internship. Judge whether the real dates can cover February–June 2027. Longer
  can fit; shorter needs clarification.
- When the whole substantive announcement is in Japanese and no exact level is
  stated, label it `Japanese-only (inferred)` and keep it in the main list. That
  is not the same as an employer explicitly requiring native fluency.
- Exclude candidate-paid placement programmes. Relocation costs are not that.
- Keep expired opportunities, clearly labelled.
- Never let a company or role reappear across search cycles.
- Keep the interface compact, practical, polished, and able to scale to hundreds
  of applications.

## Verifying before you ship

- If you cannot verify it, do not ship it.
- Tests: `.venv/bin/python manage.py test` and `.venv/bin/python manage.py check`.
- Look at the page yourself: `.venv/bin/python tools/screenshot.py /inbox/` writes
  a PNG to `.screenshots/`. It starts its own throwaway server on a free port, so
  his `runserver` keeps working. Flags: `--width 480`, `--viewport-only`,
  `--wait-ms`. It reports the HTTP status and any JavaScript errors.
- Screenshot every template, CSS or layout change before committing and before
  asking him to look. Asking him to be your eyes is a last resort.
- Tests and `curl` run in a fresh process; his browser does not. Neither proves
  the page renders for him.
- After adding any new Python file, tell him to restart the server. Django does
  not always pick up new files while running.
- If a limitation blocks verification, fix the limitation. Do not build a manual
  workflow around it and hand him the work.

## Two assistants, one repository

Codex and Claude cannot see each other. Git is the only place they meet.

1. Run `git status --short` and read the last few commits before editing. If
   there are changes you did not make, ask whether the other assistant is
   mid-task. Never overwrite work you cannot explain.
2. One focused change at a time.
3. Commit before you stop, and only after the tests pass. Uncommitted work is
   invisible to the other assistant and is lost when a session is cleared.
4. Write the commit message for someone who was not there: what was wrong, what
   you changed, what you could not verify. That message is the handover.
5. Update the notes in the same commit — the list below for an unfinished
   problem, `README.md` for behaviour, `LESSONS.md` for a mistake he corrected.
   A fix that is not written down will be re-broken.

## Outstanding work

Write every item as the thing Francesco sees, in his words. Keep the code detail
in the indented note underneath, for you, not for him. Order by how much it hurts
him, not by how interesting it is to fix. Delete an item when it is fixed; add one
the day he reports it.

- **The Inbox does nothing.** He pastes a vacancy, a link, a screenshot or a PDF
  and it just sits there. Nothing researches it, nothing turns it into a row he
  can act on. This is the biggest hole in the app.
  *Note: the capture side works; there is no analysis step wired to it.*
- **The searches still bring back weak results.** His words: not good enough.
  Every search now keeps its workings and learns from the good/bad button he
  presses on a result, so before touching how Robert is asked to search, read
  what he actually flagged as bad. Do not guess.
  *Note: `SearchCycle.raw_results`/`rejections`, `quality_flag`, `_quality_feedback()`.*
- **One search may be looking too little to find twelve good things.** A search
  is allowed eight looks around the web but is asked for up to twelve findings.
  More looking costs more money per search, so it is his decision, not yours.
  *Note: `max_tool_calls=8` in `research_internships()` in `ai.py`, discovery call only.*
- **The cost shown per researched internship is a guess.** About four cents was
  invented, never measured. After a real deep run, tell him what it truly cost
  and replace the number.
  *Note: `RESEARCH_WEB_COST` in `ai.py`.*
- **Nine Indeed links can never be checked automatically.** Indeed blocks robots,
  so those rows stay "not checked" forever. That is honest, not a bug — never
  treat "not checked" as proof a job is dead.
- **A detail panel still says "Research needed" as if it were a fact about the
  company.** Same wrong fallback that was already removed from the list columns.
- **The little symbols around the app are a mismatched set.** A proper icon set
  was tried and reverted because it crashed his running server. Redo it carefully
  and tell him to restart the server before he looks.
  *Note: reverted in `d327198` / `6859116`.*
- **Robert can see internships from campaigns Francesco is not working on.** The
  twenty most recent are pulled across all campaigns instead of the current one.
  *Note: `_compact_app_context()` in `ai.py`.*

## Keeping these notes worth reading

Anything not written down is gone when a session is cleared. But length has a
cost: past about 150 lines these files stop helping and start burying the rules
that matter. Before adding a rule here, delete one that no longer earns its
place, or write it in `LESSONS.md` instead. Only genuine repeat mistakes and
facts an assistant cannot work out from the code belong in this file.
