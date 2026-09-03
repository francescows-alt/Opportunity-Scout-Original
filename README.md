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
- Pause or activate campaigns
- Add and edit advertised jobs or cold-outreach targets
- Search and filter applications, with pagination for large lists
- Track match score, status, next action, deadlines, and CV submission date
- Save a long personal description
- Upload several profile documents locally in one step
- Quickly capture pasted vacancies, company ideas, links, screenshots, and PDFs
- Hold new inputs in a job inbox until truthful AI analysis is connected
- Keep local personal data out of Git

The application does not yet search the web, call paid APIs, send messages, or
submit applications.
