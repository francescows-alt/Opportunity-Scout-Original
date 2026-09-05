# Claude project handoff

This is Francesco's private local internship-search application. Read `README.md`,
`LESSONS.md` and the latest Git history before changing anything.

`LESSONS.md` is the mistake log for both Claude and Codex. Every rule below came
from a real failure recorded there. When Francesco corrects you, add the entry
yourself, the same day, without being asked.

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

## Outstanding work

Known problems, roughly in priority order. Keep this list current: delete an item
when it is fixed, add one when Francesco reports something that is not fixed today.

- **Inbox items are never analysed by AI.** The Inbox accepts pasted vacancies,
  links, screenshots and PDFs, but nothing turns them into researched
  opportunities. Highest-value gap.
- **Search quality is not good enough.** Francesco's words. The evidence layer
  now exists (`b13be4a`): each `SearchCycle` stores `raw_results` and
  `rejections`, every opportunity links back to its `search_cycle`, and the
  detail panel has a good/bad button writing `quality_flag` and `quality_note`.
  The loop is closed: `_quality_feedback()` sends his flags into every later
  search as USER VERDICTS. Each search now learns from the last. Still do not
  guess at prompt wording — read his flags first.
- **`max_tool_calls=8` versus "up to 12 results"** in `ai.py` `research_internships()`.
  This is the DISCOVERY call only; research was fixed separately. Eight web
  searches cannot support twelve well-sourced findings. Raising it raises the
  per-search cost, so it is his call.
- **Research cost is estimated, not measured.** `RESEARCH_WEB_COST` in `ai.py` is
  a guess of $0.04 per internship. Replace it with a real figure once a deep run
  has happened, and tell him what it actually cost.
- **9 Indeed links can never be auto-checked.** Indeed serves HTTP 401 to any
  automated browser, so those rows sit at `unchecked` forever. That is honest, not
  a bug — never let `unchecked` count as evidence against a vacancy.
- **The detail panel still shows "Research needed" as a company fact** in the
  company strip, the same fallback that was removed from the list columns.
- **Icons are inconsistent Unicode glyphs.** An SVG icon set was attempted and
  reverted in `d327198` / `6859116` after it crashed the running server. Redo it
  carefully, and tell Francesco to restart the server before he looks.
- **`ai.py` `_compact_app_context()` is not campaign-scoped.** Robert sees the 20
  most recent opportunities across every campaign, not just the active one.

## Restarting after a break

Anything not written down is gone when a session is cleared. Before finishing a
piece of work, put it somewhere durable: code and tests in Git, behaviour in
`README.md`, unfinished problems in the list above.

The OpenAI key is stored locally in `.env`. Never print, expose, or commit it.
