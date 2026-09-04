"""Load a saved application link in a real browser and report what is actually there.

Why a browser and not an HTTP request: modern applicant-tracking systems serve a
JavaScript shell that returns HTTP 200 for *any* job id. Tencent's Workday board
returns 200 for a requisition that does not exist, so a status-code checker would
have called the invented Tencent "Marketing Intern" healthy. Rendering the page is
the only way to see that Workday fell back to its generic "Careers" title.

This module never concludes that something is fake. It reports what it saw. A page
it could not read is `unchecked`, never evidence of anything.
"""

import re

from django.utils import timezone

from .models import Opportunity


# Words that appear in almost every internship title and so prove nothing about
# whether *this* vacancy is on the page.
TITLE_STOPWORDS = {
    "intern", "interns", "internship", "internships", "the", "and", "for", "of",
    "a", "an", "at", "in", "on", "to", "job", "jobs", "career", "careers", "role",
    "position", "opportunity", "opportunities", "student", "students", "program",
    "programme", "open", "apply", "application", "new", "graduate", "graduates",
    "full", "time", "part", "paid", "unpaid", "remote", "hybrid", "onsite",
}

# A rendered title that is only these words is a careers index, not a vacancy.
LANDING_PAGE_TITLES = {
    "careers", "career", "jobs", "job", "internship", "internships",
    "recruit", "recruitment", "join us", "work with us", "vacancies",
}

PAGE_TIMEOUT_MS = 45000
SETTLE_TIMEOUT_MS = 12000
SETTLE_MS = 2500


def _significant_words(value):
    normalized = re.sub(r"[^a-z0-9]+", " ", (value or "").lower())
    return {word for word in normalized.split() if word and word not in TITLE_STOPWORDS}


def _looks_like_landing_page(page_title):
    stripped = re.sub(r"[^a-z0-9 ]+", " ", (page_title or "").lower())
    # Titles are usually "Careers | Company" or "Career – Company"; keep the first part.
    lead = stripped.split("  ")[0].strip()
    return lead in LANDING_PAGE_TITLES or stripped.strip() in LANDING_PAGE_TITLES


# A URL that points at one specific posting rather than a careers index: an ATS
# job path, or a requisition id such as R107154.
SPECIFIC_POSTING_PATTERNS = (
    re.compile(r"/job/|/jobs/[^/]+/|/postings?/|/vacanc", re.I),
    re.compile(r"[_/-][A-Z]{1,3}\d{5,}"),
    re.compile(r"[?&](jk|gh_jid|jobid)=", re.I),
)


def _is_specific_posting_url(url):
    return any(pattern.search(url or "") for pattern in SPECIFIC_POSTING_PATTERNS)


def judge_page(role_title, page_title, body_text, source_url=""):
    """Decide what a rendered page says about one vacancy. Pure, so it is testable
    without a browser and without the network."""
    wanted = _significant_words(role_title)
    seen_title = _significant_words(page_title)
    if wanted and wanted & seen_title:
        return Opportunity.LinkCheck.CONFIRMED, f"Page title: {page_title!r}"
    # The vacancy title may live in the body rather than the document title.
    body_words = _significant_words(body_text[:20000])
    if wanted and len(wanted & body_words) >= max(2, len(wanted) // 2):
        return Opportunity.LinkCheck.CONFIRMED, f"Role wording found in the page text. Title: {page_title!r}"
    if _looks_like_landing_page(page_title):
        # A URL promising one specific posting that renders the site's generic
        # title is how a fabricated requisition id looks. A company careers index
        # showing a careers title is just the wrong link.
        if _is_specific_posting_url(source_url):
            return (
                Opportunity.LinkCheck.NOT_FOUND,
                f"The link points at one specific posting, but the page fell back to the site's "
                f"general title {page_title!r}. That usually means this posting does not exist.",
            )
        return (
            Opportunity.LinkCheck.LANDING_PAGE,
            f"This is a general careers page, not this vacancy. Page title: {page_title!r}",
        )
    return (
        Opportunity.LinkCheck.NOT_FOUND,
        f"The page loaded but showed no sign of this vacancy. Page title: {page_title!r}",
    )


_DONE = object()


def check_links(opportunities):
    """Yield (opportunity, status, note) as each link is rendered.

    Costs nothing and calls no AI.

    The browser runs in its own thread on purpose. `sync_playwright()` installs an
    asyncio event loop in whatever thread it runs in, and Django's ORM refuses to
    run inside one — saving a result from inside the browser's thread raises
    SynchronousOnlyOperation. Keeping the browser over here lets the caller save
    each result as it arrives, on a thread that can still talk to the database.
    """
    import queue
    import threading

    from playwright.sync_api import sync_playwright

    outbox = queue.Queue()

    def worker():
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
                    )
                )
                try:
                    for opportunity in opportunities:
                        outbox.put((opportunity,) + _check_one(context, opportunity))
                finally:
                    context.close()
                    browser.close()
        except Exception as error:
            # The browser itself failed. Report every row as uncheckable rather
            # than letting a missing browser look like missing vacancies.
            note = f"The checking browser could not start ({type(error).__name__})."
            for opportunity in opportunities:
                outbox.put((opportunity, Opportunity.LinkCheck.UNCHECKED, note))
        finally:
            outbox.put(_DONE)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    while True:
        item = outbox.get()
        if item is _DONE:
            break
        yield item


def _check_one(context, opportunity):
    if not opportunity.source_url.strip():
        return Opportunity.LinkCheck.UNCHECKED, "No application link was saved."
    page = context.new_page()
    try:
        # Load, then give the page a bounded chance to settle. Waiting for full
        # network idle up front times out on any site with analytics or polling,
        # which would wrongly report a real vacancy as uncheckable. Waiting for
        # nothing reports a real vacancy as missing, because an ATS renders its
        # title in JavaScript. So: load, then settle if it can, then read.
        response = page.goto(opportunity.source_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        try:
            page.wait_for_load_state("networkidle", timeout=SETTLE_TIMEOUT_MS)
        except Exception:
            pass
        page.wait_for_timeout(SETTLE_MS)
        http_status = response.status if response else 0
        if http_status >= 400:
            # Indeed and similar serve 403 to any automated browser. That says
            # nothing about the vacancy, so it must never count against it.
            return (
                Opportunity.LinkCheck.UNCHECKED,
                f"The site refused an automated visit (HTTP {http_status}). Open it yourself to judge.",
            )
        try:
            body_text = page.inner_text("body")
        except Exception:
            body_text = ""
        return judge_page(opportunity.title, page.title(), body_text, opportunity.source_url)
    except Exception as error:
        return (
            Opportunity.LinkCheck.UNCHECKED,
            f"Could not load the page ({type(error).__name__}). This is not evidence against the vacancy.",
        )
    finally:
        page.close()


def record_result(opportunity, status, note):
    opportunity.link_check_status = status
    opportunity.link_check_note = note[:2000]
    opportunity.link_checked_at = timezone.now()
    opportunity.save(update_fields=["link_check_status", "link_check_note", "link_checked_at", "updated_at"])
