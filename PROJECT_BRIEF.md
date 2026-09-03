# Job Search Assistant — Project Brief

## Purpose

Build a private, reusable application that helps a person discover, evaluate,
research, contact, and track suitable job opportunities. The first use case is
Francesco's graduation-internship search in Japan for February–June 2027, but
the software must not hard-code that search into the product.

## Non-negotiable rules

- Keep the initial version free to run locally.
- Explain any possible paid service and obtain approval before enabling it.
- Never apply, send an email, or contact anyone without the user's explicit
  approval of the exact action and content.
- Never invent education, experience, skills, language ability, achievements,
  or other claims.
- Keep verified facts separate from assumptions and AI-generated conclusions.
- Store the source and retrieval date for job, company, and contact information.
- Use public professional contact information only. Do not collect leaked,
  hidden, or private personal contact information.
- Make search preferences editable and support multiple searches over time.

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

## First working version

The first version will run only on the user's computer and will not use paid
APIs. It will allow the user to:

- create and edit a search campaign;
- manually add an organization or opportunity;
- view and edit saved opportunities;
- move an opportunity through a configurable pipeline;
- record notes, source links, deadlines, and activity history;
- keep advertised opportunities distinct from cold-outreach targets.

It will not yet search the web, evaluate fit with AI, find contacts, draft
messages, send messages, or submit applications.

## Cost policy

- Local application, programming language, framework, database, tests, Git,
  and GitHub: target cost of zero.
- Prefer public pages, permitted feeds, official APIs with useful free tiers,
  and manual imports before paid data services.
- AI inside the future application may require separately billed API usage.
  It must be optional, usage-limited, and visible to the user.
- Reliable daily operation may eventually require low-cost hosting because a
  sleeping laptop cannot run searches. This is not required for version one.
- Show estimated or actual usage costs in the product before automations run.

## Decisions still needed

- Exact university internship and thesis requirements
- Verified education, experience, skills, achievements, and languages
- Location, industry, organization, compensation, and schedule priorities
- Deal-breakers and acceptable compromises
- Countries where the user is legally able to work and visa situation
- Preferred outreach style and contact boundaries
- Whether a future multi-user version is personal, shared privately, or public
