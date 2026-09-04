# Opportunity Scout

A private, reusable job-search dashboard. The current version manages editable
search campaigns, applications, companies, a personal profile, and local
supporting documents. Later versions will add research, evaluation, outreach
drafts, and approval-controlled automation.

## Run it on this Mac

Open a terminal in this folder and run:

```bash
.venv/bin/python manage.py runserver
```

Then open <http://127.0.0.1:8000/> in a browser.

The application runs only while that terminal command is active. Press
`Control+C` in the terminal to stop it.

## Run the automated checks

```bash
.venv/bin/python manage.py test
```

## Current scope

- Create search campaigns
- Edit every campaign requirement and preference
- Keep each campaign as a separate sheet of job hunting: exactly one is in use at
  a time, Applications shows only that campaign's saved roles, and switching is
  one click on the Search rules page. Nothing is deleted when you switch.
- Add and edit advertised jobs or cold-outreach targets
- Search and filter applications, with pagination for large lists
- Track match score, status, next action, deadlines, and CV submission date
- Save a long personal description
- Talk with Robert in a profile interview that maintains an editable live draft
- Upload several profile documents locally in one step
- Quickly capture pasted vacancies, company ideas, links, screenshots, and PDFs
- Analyze job-inbox material and run source-backed web research with Robert
- Run complete search cycles with visible progress, duplicate and fee checks
- Keep a record of what each search returned and what was filtered out, and mark
  any result good or bad. Every later search is told about those verdicts, so the
  searches get more tailored to you each time you use them
- Open every saved application link in a real browser to check the vacancy is
  actually there, and move invented ones to a Deleted folder you can undo
- Research each internship in its own deep pass, five running at a time, so every
  company gets a full set of web searches instead of sharing one with seven others
- Build campaigns conversationally with Robert, then edit every setting manually
- Ask Robert for hiring advice from anywhere in the app
- Record reliable dictation and transcribe it into important text areas
- Keep local personal data out of Git

The application does not send messages or submit applications. Searches begin
only when the user starts them; future scheduling and email sync are not built yet.

## One-time AI setup

Robert and dictation use the OpenAI API. API billing is separate from a ChatGPT
or Codex subscription, although you can sign in with the same OpenAI account.

1. Add $10 of prepaid API credit at <https://platform.openai.com/settings/organization/billing/overview>.
2. Turn automatic recharge off if you want the simplest spending protection.
3. Create a secret key at <https://platform.openai.com/api-keys>.
4. In the project terminal, run `cp .env.example .env`.
5. Open `.env`, replace `your-key-goes-here` with the secret key, and save it.
6. Stop and restart the local server.

Never paste the secret key into chat. The real `.env` is ignored by Git. The app
also pauses its own AI calls when its estimated monthly usage reaches $9; this is
a second safety guard, not a substitute for checking the OpenAI billing page.
