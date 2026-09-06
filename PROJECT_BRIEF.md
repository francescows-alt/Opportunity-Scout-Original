# Job Search Assistant — Project Brief

## Purpose

Build a private, reusable application that helps a person discover, evaluate,
research, contact, and track suitable job opportunities. The first use case is
Francesco's graduation-internship search in Japan for February–June 2027, but
the software must not hard-code that search into the product.

## Non-negotiable rules

These live in one place only, `CLAUDE.md`, so they cannot drift apart: never act
on his behalf, never invent a fact, never spend without his click, keep verified
facts separate from assumptions, store the source and date of every job and
company fact, and use public professional contact information only.

Search preferences must stay editable, and the software must support many
searches over time. The first campaign below is not a permanent limitation.

## Current search campaign

This is the first campaign, not a permanent software limitation.

- Goal: graduation internship
- Period: February–June 2027
- Preferred location: Japan, especially Tokyo
- Work style: remote or hybrid preferred
- Organization type: open to multinationals, major Japanese companies,
  startups, scale-ups, SMEs, research organizations, and other credible
  organizations
- Organization judgment: prioritize substantive work, learning, credible
  responsibility, career signal, useful connections, and CV value—not size or
  prestige alone
- Preferred work themes (guidance, not strict filters):
  - marketing and growth
  - sales and business development
  - market and customer research
  - creating and testing campaigns
  - performance analysis
  - finding customers or partners
  - strategic projects
- Academic need: must support an applied business-research project and qualify
  under the university's graduation-internship rules
- Japan-specific needs:
  - intermediate Japanese must be acceptable
  - native or fluent Japanese must not be mandatory
  - visa support must be available if relocation requires it
- Personal constraint: enough flexibility to complete a university thesis and
  continue developing a personal business outside internship hours
- Work-life balance: avoid environments with strong evidence of excessive
  hours, rigid presenteeism, or an unhealthy ultra-traditional culture; do not
  reject a Japanese company merely because it is large or traditional
- Exclude low-substance placements whose main work is reception, repetitive
  administration, generic errands, or other duties that provide little
  learning, responsibility, research access, or career value
- Judgment rule: recommend strong opportunities outside the preferred themes
  when the work is substantive, academically viable, realistically attainable,
  and likely to improve the user's skills, network, reputation, or future CV

## University requirements known so far

Programme: Hogeschool Rotterdam / Rotterdam Business School, International
Business, Asia track (Japanese).

The public university pages currently establish that:

- the final semester includes a 30 EC thesis;
- the student chooses a business topic;
- the programme expects an international and interculturally aware business
  context;
- general Hogeschool Rotterdam guidance says a graduation organization should
  have at least four people and a supervisor with relevant expertise at at
  least Dutch HBO (university-of-applied-sciences) level.

These are incomplete, provisional requirements. Before automatically deciding
that an opportunity qualifies, the system needs the current International
Business graduation manual, assessment rubric, thesis-start documentation,
and written confirmation of any Japan, supervision, company-size, working-hour,
research-access, and February–June 2027 requirements.

## Main product areas

1. Search campaigns: editable descriptions of what a user is looking for.
2. Profile: verified facts about the user, with supporting evidence.
3. University requirements: rules an opportunity must satisfy.
4. Organizations: companies, startups, universities, institutes, and NGOs.
5. Opportunities: advertised roles and possible cold-outreach opportunities.
6. Evaluation: fit, concerns, missing information, and disqualifying facts.
7. Contacts: public professional contacts with source links and retrieval dates.
8. Documents and outreach: truthful drafts that require approval.
9. Pipeline: stages and a history of actions, decisions, and outcomes.
10. Automation: searches and reminders with limits, logs, and approval gates.

## What the app does today

See "Current scope" in `README.md`, which is kept current. In short: it runs
locally, creates and edits campaigns, searches the web with AI, researches each
opportunity with sources, captures pasted vacancies and files, evaluates fit,
and tracks everything through a pipeline. It does not send messages or submit
applications, and it never will without his approval of the exact content.

## Cost policy

Paid AI is now in use and is no longer free to run; the money rule in `CLAUDE.md`
governs every call. What remains true here: prefer public pages, permitted feeds
and official free tiers before paid data services, show the estimated or actual
cost in the product before an automation runs, and expect that reliable daily
operation may one day need low-cost hosting, because a sleeping laptop cannot run
searches.

## Decisions still needed

- Exact university internship and thesis requirements
- Verified education, experience, skills, achievements, and languages
- Location, industry, organization, compensation, and schedule priorities
- Deal-breakers and acceptable compromises
- Countries where the user is legally able to work and visa situation
- Preferred outreach style and contact boundaries
- Whether a future multi-user version is personal, shared privately, or public
