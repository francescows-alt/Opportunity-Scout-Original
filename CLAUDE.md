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

The OpenAI key is stored locally in `.env`. Never print, expose, or commit it.
