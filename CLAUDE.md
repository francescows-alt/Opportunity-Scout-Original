# Claude project handoff

This is Francesco's private local internship-search application. Read `README.md`
and the latest Git history before changing anything.

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
- Default to under 200 words. Write a long report only when Francesco asks.
- Say what you cannot verify BEFORE doing the work, not afterwards.

## Verification

- If you cannot verify it, do not ship it. Claude has no browser here: it can
  run tests and read raw HTML, but cannot see the rendered page.
- Never commit CSS, template or layout changes until Francesco has confirmed
  they look right in the browser.
- After adding any new Python file, tell Francesco to restart the server.
  Django does not always pick up new files while running.

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
- **Search quality is not good enough.** Francesco's words. Needs a concrete
  example of a bad result before touching the prompts — searches cost real money
  and cannot be re-run freely to test a guess.
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
