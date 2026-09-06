# Project handoff

Read this whoever you are. `AGENTS.md` and `CLAUDE.md` are the same file, so Codex
and Claude get identical instructions and neither can drift off on its own set of
rules.

This is Francesco's private local internship-search application. Read
`PROJECT_BRIEF.md` for what it is for, then `README.md`, `LESSONS.md` and the
latest Git history, before changing anything.

`LESSONS.md` is the shared mistake log. Every rule below came from a real failure
recorded there. When Francesco corrects you, add the entry yourself, the same day,
without being asked, so the other assistant cannot repeat it.

Francesco is not an engineer. He cannot review your code, so the only way he can
judge your work is by using the app and by what you tell him. That makes an
unverified claim of success worse than saying you are stuck.

## Product rules

- Explain software simply: the owner is a beginner.
- Robert researches truthfully and cites sources. Never invent candidate or job facts.
- Never apply, email, contact, or submit anything without explicit user approval.
- Do not require an employer to call a role a "graduation" or "thesis" internship.
  Judge whether the real dates can cover February–June 2027. Longer can fit;
  shorter needs clarification.
- Language rule: when the whole substantive announcement is in Japanese and no
  exact Japanese level is stated, classify and visibly label it `Japanese-only
  (inferred)`. Keep it in the main list for reference. Do not confuse this
  inference with an employer explicitly requiring native fluency.
- Exclude candidate-paid placement programs; do not confuse these with relocation costs.
- Preserve expired opportunities but label them clearly.
- Prevent duplicate companies/roles across repeated search cycles.
- Keep the interface compact, practical, visually polished, and able to scale to
  hundreds of applications.

## Communication

- Lead with the blocker, limitation or risk in the FIRST line. Never bury it.
- Be concise. Default to under 150 words. Long reports only when he asks.
- Say what you cannot verify BEFORE doing the work, not afterwards.
- No code in what you say to him. No file names, function names, settings,
  commit hashes or field names. He is not an engineer and cannot check them.
  Name the thing he sees on screen and what it does wrong. Keep the code detail
  in this file and in commit messages, where it belongs.
- Never hand him a list of problems as an opening. Tell him the one that hurts
  most and what you propose to do about it.

## Do not ask permission

Run every command and make every ordinary change without asking, then report what
you did. Stop and ask for only two things:

1. **Spending money** — a Robert search, research run or inbox analysis. His click.
   Never infer this from "make it work", "fix it", "go" or "just do everything".
   Those authorise building and mocked tests, never a real paid call. Build the
   feature, test it with mocks, then hand him the button.
2. **Design direction** — a visual or product taste decision that is genuinely his.

Commands, refactors, migrations, fixes, tests and commits: just do them. The
safety rules are separate and never relax — never read or print `.env`, never
apply, email or contact anyone.

## Verification

- If you cannot verify it, do not ship it.
- **Look at the page yourself.** Run
  `.venv/bin/python tools/screenshot.py /inbox/` and open the PNG it writes to
  `.screenshots/`. It starts its own throwaway server on a free port, so
  Francesco's `runserver` can keep running. Useful flags: `--width 480` for
  mobile, `--viewport-only`, `--wait-ms`. The script reports the HTTP status and
  any JavaScript errors.
- Screenshot every template, CSS or layout change **before** committing it, and
  before asking Francesco to look. Asking him to be your eyes is a last resort,
  not the process.
- Tests and `curl` run in a fresh process; his browser does not. Neither proves
  the page renders for him.
- After adding any new Python file, tell Francesco to restart the server.
  Django does not always pick up new files while running.
- If a limitation is blocking verification, fix the limitation. Do not build a
  workflow around it and hand him the manual work. See `LESSONS.md`.

## Development workflow

1. Run `git status --short` and read recent commits before editing.
2. Never overwrite unexplained existing changes. Ask if another assistant may be editing.
3. Make one focused change at a time.
4. Run `.venv/bin/python manage.py test` and `.venv/bin/python manage.py check`.
5. Tell Francesco what changed in plain language.
6. Make a Git checkpoint only after tests pass.

## Two assistants, one repository

Codex and Claude both work here, and they cannot see each other. Git is the only
place they meet.

1. Start by running `git status --short` and reading the last few commits. If
   there are changes you did not make, stop and ask Francesco whether the other
   assistant is mid-task. Never overwrite work you cannot explain.
2. Finish and commit before you stop. Uncommitted work is invisible to the other
   assistant and is lost when a session is cleared.
3. Write commit messages for a person who was not there: what was wrong, what you
   changed, and what you could not verify. That message is the handover.
4. Keep the notes current in the same commit as the change — the outstanding-work
   list below, `README.md` for behaviour, `LESSONS.md` for a mistake. A fix that
   is not written down will be re-broken.

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

## Restarting after a break

Anything not written down is gone when a session is cleared. Before finishing a
piece of work, put it somewhere durable: code and tests in Git, behaviour in
`README.md`, unfinished problems in the list above.

The OpenAI key is stored locally in `.env`. Never print, expose, or commit it.
