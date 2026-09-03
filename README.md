# Opportunity Scout

A private, reusable job-search dashboard. The first version manages editable
search campaigns; later versions will add organizations, opportunities,
research, evaluation, outreach drafts, and approval-controlled automation.

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
- Keep local personal data out of Git

The application does not yet search the web, call paid APIs, send messages, or
submit applications.

