import hashlib
import logging
from datetime import timedelta
from pathlib import Path
import re
from threading import Thread
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db import close_old_connections, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .ai import AIUnavailable, analyze_inbox_item, analyze_profile_documents, campaign_reply, is_configured, profile_reply, qualify_opportunities, research_internships, robert_reply, transcribe

logger = logging.getLogger(__name__)

from .forms import (
    CampaignPromptForm,
    OpportunityForm,
    LinkedInSourceForm,
    ProfileDocumentUploadForm,
    ProfileSourceNotesForm,
    QuickInboxForm,
    SearchCampaignForm,
)
from .models import CandidateProfile, ChatMessage, InboxItem, Opportunity, Organization, ProfileDocument, SearchCampaign, SearchCycle, SearchJob


GENERIC_QUALIFICATION_TERMS = (
    "proactive", "self-motivated", "motivated", "passionate", "team player",
    "positive attitude", "can-do attitude", "flexible working style",
    "responsible work", "reliable and consistent", "willingness to learn",
    "initiative and ability to work independently", "ability to work independently",
    "excellent communication", "clear communication", "self-directed remote work",
)


def _is_concrete_qualification(requirement):
    normalized = " ".join(requirement.lower().split())
    return bool(normalized) and not any(term in normalized for term in GENERIC_QUALIFICATION_TERMS)


def _canonicalize_url(url):
    parsed = urlsplit(url.strip())
    host = parsed.netloc.lower().removeprefix("www.")
    path = re.sub(r"/+", "/", parsed.path).rstrip("/") or "/"
    stable_keys = {"jk", "jobid", "gh_jid", "lever-source"}
    query = urlencode(sorted(
        (key.lower(), value) for key, value in parse_qsl(parsed.query)
        if key.lower() in stable_keys
    ))
    return urlunsplit(("https", host, path, query, ""))


TRACKING_QUERY_PREFIXES = ("utm_", "mc_", "pk_")
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "msclkid", "igshid", "ref", "ref_src", "trk", "trkcampaign"}


def _strip_tracking(url):
    """Keep the link a human can click, minus the analytics junk that rides along
    when a page is shared. `utm_source=chatgpt.com` in a saved vacancy looks wrong."""
    parsed = urlsplit(url.strip())
    kept = [
        (key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS
        and not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    ]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(kept), parsed.fragment))


def _plain_text(value):
    """Robert sometimes cites sources as Markdown links. Templates show raw text,
    so flatten `[label](url)` to `label` before storing anything user-visible."""
    return re.sub(r"\[([^\]]+)\]\((?:[^)]+)\)", r"\1", value).strip()


LOGO_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".ico")


def _looks_like_logo_image(url):
    """Reject bare homepage links; only accept URLs that point at an actual image file."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return parsed.path.lower().endswith(LOGO_IMAGE_EXTENSIONS)


def _normalized_words(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _opportunity_fingerprint(company, title, location):
    identity = "|".join((_normalized_words(company), _normalized_words(title), _normalized_words(location)))
    return hashlib.sha256(identity.encode()).hexdigest()


def _score_tone(score):
    if score is None:
        return "unknown"
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "strong"
    if score >= 50:
        return "mixed"
    return "low"


def _selected_alert(opportunity):
    today = timezone.localdate()
    if opportunity.candidate_fee_required:
        return {"tone": "danger", "icon": "⊘", "title": "Candidate fee required", "text": f"This program charges you {opportunity.candidate_fee or 'a mandatory fee'} and is unsuitable."}
    if opportunity.verification_status == Opportunity.VerificationStatus.EXPIRED:
        return {"tone": "danger", "icon": "⌛", "title": "This vacancy is expired", "text": "Do not spend application time on it."}
    if opportunity.verification_status == Opportunity.VerificationStatus.UNSUITABLE:
        return {"tone": "danger", "icon": "×", "title": "Robert marked this unsuitable", "text": opportunity.next_action or "A verified requirement conflicts with your search."}
    if opportunity.deadline:
        days_left = (opportunity.deadline - today).days
        if days_left < 0:
            return {"tone": "danger", "icon": "⌛", "title": "Deadline passed", "text": f"The deadline was {opportunity.deadline:%-d %b %Y}."}
        if days_left <= 14:
            return {"tone": "warning", "icon": "!", "title": f"Deadline in {days_left} days", "text": "Review and prepare this application now."}
    if opportunity.verification_status == Opportunity.VerificationStatus.QUALIFIED and (opportunity.match_score or 0) >= 85:
        return {"tone": "success", "icon": "★", "title": "High-priority match", "text": "The verified evidence makes this one worth serious attention."}
    return None


def home(request):
    return redirect("dashboard")


def _incomplete_research_filter():
    """The single definition of 'needs research' shared by the dashboard count,
    the manual retry button, and the background research runner, so they never drift."""
    return (
        Q(verification_status=Opportunity.VerificationStatus.PENDING)
        | Q(company_country="")
        | Q(company_industry="")
        | Q(what_you_would_do="")
        | Q(what_company_needs="")
        | Q(candidate_fee="")
        | Q(compensation="")
        | Q(posting_language="")
        | Q(minimum_duration="")
    )


def dashboard(request):
    # Each campaign is a separate job-hunt sheet: only the selected one is shown.
    active_campaign = SearchCampaign.objects.filter(is_active=True).first()
    campaign_opportunities = (
        Opportunity.objects.filter(campaign=active_campaign)
        if active_campaign else Opportunity.objects.none()
    )
    opportunities = campaign_opportunities.select_related("campaign", "organization")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    review = request.GET.get("review", "").strip()
    if query:
        opportunities = opportunities.filter(
            Q(organization__name__icontains=query)
            | Q(title__icontains=query)
            | Q(location__icontains=query)
        )
    if status:
        opportunities = opportunities.filter(status=status)
    incomplete_research = _incomplete_research_filter()
    if review == "serious":
        opportunities = opportunities.filter(verification_status=Opportunity.VerificationStatus.QUALIFIED)
    elif review == "clarify":
        opportunities = opportunities.filter(verification_status=Opportunity.VerificationStatus.CLARIFY)
    elif review == "research":
        opportunities = opportunities.filter(incomplete_research)
    elif review == "favorites":
        opportunities = opportunities.filter(is_favorite=True)
    elif review == "not_suitable":
        opportunities = opportunities.filter(verification_status__in=[
            Opportunity.VerificationStatus.UNSUITABLE,
            Opportunity.VerificationStatus.EXPIRED,
            Opportunity.VerificationStatus.UNVERIFIED,
        ])

    paginator = Paginator(opportunities, 25)
    page = paginator.get_page(request.GET.get("page"))
    selected = None
    selected_id = request.GET.get("selected")
    if selected_id:
        selected = opportunities.filter(id=selected_id).first()
    completed_job_id = request.GET.get("search_complete", "")
    completed_search_job = (
        SearchJob.objects.filter(pk=completed_job_id, status=SearchJob.Status.COMPLETE).first()
        if completed_job_id.isdigit() else None
    )
    fresh_ids = set(completed_search_job.opportunity_ids if completed_search_job else [])
    for opportunity in page.object_list:
        opportunity.match_tone = _score_tone(opportunity.match_score)
        opportunity.is_fresh = opportunity.id in fresh_ids
    if selected:
        selected.match_tone = _score_tone(selected.match_score)

    all_opportunities = campaign_opportunities
    research_needed_count = all_opportunities.filter(incomplete_research).count()
    context = {
        "page": page,
        "selected": selected,
        "query": query,
        "current_status": status,
        "current_review": review,
        "statuses": Opportunity.Status.choices,
        "tracked_count": all_opportunities.count(),
        "draft_count": all_opportunities.filter(status=Opportunity.Status.DRAFT_READY).count(),
        "sent_count": all_opportunities.filter(submitted_on__isnull=False).count(),
        "action_count": all_opportunities.exclude(next_action="").exclude(
            status__in=[Opportunity.Status.REJECTED, Opportunity.Status.OFFER]
        ).count(),
        "active_campaign": active_campaign,
        "ai_configured": is_configured(),
        "research_needed_count": research_needed_count,
        "serious_count": all_opportunities.filter(
            verification_status=Opportunity.VerificationStatus.QUALIFIED,
        ).count(),
        "clarify_count": all_opportunities.filter(
            verification_status=Opportunity.VerificationStatus.CLARIFY,
        ).count(),
        "favorites_count": all_opportunities.filter(is_favorite=True).count(),
        "selected_alert": _selected_alert(selected) if selected else None,
        "active_search_job": SearchJob.objects.filter(
            status__in=[SearchJob.Status.QUEUED, SearchJob.Status.RUNNING],
        ).order_by("-created_at").first(),
        "completed_search_job": completed_search_job,
    }
    return render(request, "tracker/dashboard.html", context)


@require_POST
def toggle_favorite(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
    opportunity.is_favorite = not opportunity.is_favorite
    opportunity.save(update_fields=["is_favorite", "updated_at"])
    return redirect(f"{reverse('dashboard')}?selected={opportunity.id}")


def _internal_host():
    """Host header for the in-process client the background runners use. Django's
    test runner allows only "testserver"; a local DEBUG server allows localhost."""
    return settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


def _update_search_job(job_id, **values):
    values["updated_at"] = timezone.now()
    SearchJob.objects.filter(pk=job_id).update(**values)


def _run_complete_search(job_id):
    """Run the existing search and qualification views behind one progress ticket."""
    from django.test import Client

    close_old_connections()
    try:
        job = SearchJob.objects.select_related("campaign").get(pk=job_id)
        before_ids = set(Opportunity.objects.filter(campaign=job.campaign).values_list("id", flat=True))
        previous_cycle = SearchCycle.objects.filter(campaign=job.campaign).order_by("-sequence").first()
        previous_sequence = previous_cycle.sequence if previous_cycle else 0
        _update_search_job(job_id, status=SearchJob.Status.RUNNING, stage="searching", progress=12, message="Searching new sources and keywords…")

        client = Client(HTTP_HOST="localhost")
        client.post(reverse("discover-internships"))
        cycle = SearchCycle.objects.filter(campaign=job.campaign, sequence__gt=previous_sequence).order_by("-sequence").first()
        if cycle is None:
            raise RuntimeError("The discovery stage did not complete.")

        new_ids = list(
            Opportunity.objects.filter(campaign=job.campaign)
            .exclude(pk__in=before_ids)
            .values_list("id", flat=True)
        )
        _update_search_job(
            job_id, stage="checking", progress=38,
            message="Duplicates and candidate fees checked.",
            found_count=cycle.found_count, added_count=len(new_ids),
            duplicate_count=cycle.duplicate_count, fee_blocked_count=cycle.fee_blocked_count,
            opportunity_ids=new_ids,
        )

        total = len(new_ids)
        for offset in range(0, total, 8):
            chunk = new_ids[offset:offset + 8]
            _update_search_job(
                job_id, stage="researching",
                progress=48 + round(38 * offset / max(total, 1)),
                message=f"Deep research: {min(offset + 1, total)}–{min(offset + len(chunk), total)} of {total}…",
            )
            client.post(reverse("qualify-discoveries"), {"opportunity_ids": chunk})

        researched = Opportunity.objects.filter(pk__in=new_ids, verified_at__isnull=False).count()
        _update_search_job(job_id, stage="saving", progress=92, message="Saving reports and priority signals…", researched_count=researched)
        incomplete = total - researched
        if incomplete:
            final_message = f"Finished with {incomplete} report{'s' if incomplete != 1 else ''} needing retry."
        else:
            final_message = f"Complete: {researched} researched, {cycle.duplicate_count} duplicates blocked, {cycle.fee_blocked_count} fee programs excluded."
        _update_search_job(job_id, status=SearchJob.Status.COMPLETE, stage="complete", progress=100, message=final_message)
    except Exception as error:
        _update_search_job(
            job_id, status=SearchJob.Status.FAILED, stage="failed", progress=100,
            message="Search stopped safely. Existing information was not damaged.", error=str(error)[:1000],
        )
    finally:
        close_old_connections()


def _require_campaign_and_profile():
    """Shared precondition check for both background job starters. Returns
    (campaign, profile, error_response); error_response is None when both exist."""
    campaign = SearchCampaign.objects.filter(is_active=True).first()
    if not campaign:
        return None, None, JsonResponse({"error": "Create and activate a search campaign first."}, status=400)
    profile = CandidateProfile.objects.filter(pk=1).first()
    if not profile or not (profile.structured_profile or profile.profile_draft.strip()):
        return None, None, JsonResponse({"error": "Complete your profile before Robert searches."}, status=400)
    return campaign, profile, None


def _launch_background_job(campaign, runner):
    """Reuse one active SearchJob if one is already running, otherwise start a new
    background thread. Shared by the full search and the research-only retry."""
    stale_before = timezone.now() - timedelta(minutes=30)
    SearchJob.objects.filter(
        status__in=[SearchJob.Status.QUEUED, SearchJob.Status.RUNNING], updated_at__lt=stale_before,
    ).update(
        status=SearchJob.Status.FAILED, stage="failed", progress=100,
        message="Previous search expired safely; start a new one.", updated_at=timezone.now(),
    )
    active = SearchJob.objects.filter(status__in=[SearchJob.Status.QUEUED, SearchJob.Status.RUNNING]).order_by("-created_at").first()
    if active:
        return JsonResponse({"job_id": active.id, "status_url": reverse("search-job-status", args=[active.id])})
    job = SearchJob.objects.create(campaign=campaign)
    Thread(target=runner, args=(job.id,), daemon=True).start()
    return JsonResponse({"job_id": job.id, "status_url": reverse("search-job-status", args=[job.id])}, status=202)


@require_POST
def start_complete_search(request):
    campaign, profile, error = _require_campaign_and_profile()
    if error:
        return error
    return _launch_background_job(campaign, _run_complete_search)


def _run_research_only(job_id):
    """Finish deep research on every opportunity still incomplete for this campaign,
    looping in batches of 8 until none remain — unlike a single manual retry click."""
    from django.test import Client

    close_old_connections()
    try:
        job = SearchJob.objects.select_related("campaign").get(pk=job_id)
        pending_ids = list(
            Opportunity.objects.filter(campaign=job.campaign)
            .filter(_incomplete_research_filter())
            .order_by("-match_score", "-created_at")
            .values_list("id", flat=True)
        )
        total = len(pending_ids)
        _update_search_job(
            job_id, status=SearchJob.Status.RUNNING, stage="researching", progress=8,
            message=f"Deep research: preparing {total} report{'s' if total != 1 else ''}…",
            found_count=total, opportunity_ids=pending_ids,
        )

        client = Client(HTTP_HOST="localhost")
        for offset in range(0, total, 8):
            chunk = pending_ids[offset:offset + 8]
            _update_search_job(
                job_id, stage="researching",
                progress=8 + round(84 * offset / max(total, 1)),
                message=f"Deep research: {min(offset + 1, total)}–{min(offset + len(chunk), total)} of {total}…",
            )
            client.post(reverse("qualify-discoveries"), {"opportunity_ids": chunk})

        researched = Opportunity.objects.filter(pk__in=pending_ids, verified_at__isnull=False).count()
        _update_search_job(job_id, stage="saving", progress=95, message="Saving reports…", researched_count=researched)
        incomplete = total - researched
        if incomplete:
            final_message = f"Finished with {incomplete} report{'s' if incomplete != 1 else ''} still needing retry."
        else:
            final_message = f"Complete: {researched} report{'s' if researched != 1 else ''} researched."
        _update_search_job(job_id, status=SearchJob.Status.COMPLETE, stage="complete", progress=100, message=final_message)
    except Exception as error:
        _update_search_job(
            job_id, status=SearchJob.Status.FAILED, stage="failed", progress=100,
            message="Research stopped safely. Existing information was not damaged.", error=str(error)[:1000],
        )
    finally:
        close_old_connections()


@require_POST
def start_research_only(request):
    campaign, profile, error = _require_campaign_and_profile()
    if error:
        return error
    pending_count = Opportunity.objects.filter(campaign=campaign).filter(_incomplete_research_filter()).count()
    if not pending_count:
        return JsonResponse({"error": "There are no discoveries waiting for research."}, status=400)
    return _launch_background_job(campaign, _run_research_only)


def search_job_status(request, job_id):
    job = get_object_or_404(SearchJob, pk=job_id)
    return JsonResponse({
        "status": job.status, "stage": job.stage, "progress": job.progress,
        "message": job.message, "found": job.found_count, "added": job.added_count,
        "researched": job.researched_count, "duplicates": job.duplicate_count,
        "fees": job.fee_blocked_count, "opportunity_ids": job.opportunity_ids,
    })


@require_POST
def discover_internships(request):
    campaign = SearchCampaign.objects.filter(is_active=True).first()
    if not campaign:
        messages.error(request, "Create and activate a search campaign before Robert searches.")
        return redirect("campaign-list")
    profile = CandidateProfile.objects.filter(pk=1).first()
    if not profile or not (profile.structured_profile or profile.profile_draft.strip()):
        messages.error(request, "Finish a basic profile first so Robert can judge which internships fit you.")
        return redirect("profile")

    try:
        batch = research_internships(campaign, profile)
        added = 0
        duplicates = 0
        fee_blocked = 0
        known_urls = {
            opportunity.canonical_url or _canonicalize_url(opportunity.source_url)
            for opportunity in Opportunity.objects.filter(campaign=campaign)
            if opportunity.source_url
        }
        known_fingerprints = {
            opportunity.fingerprint or _opportunity_fingerprint(
                opportunity.organization.name, opportunity.title, opportunity.location,
            )
            for opportunity in Opportunity.objects.filter(campaign=campaign).select_related("organization")
        }
        for item in batch.opportunities:
            source_url = item.source_url.strip()
            parsed = urlparse(source_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            canonical_url = _canonicalize_url(source_url)
            fingerprint = _opportunity_fingerprint(item.company, item.title, item.location)
            if canonical_url in known_urls or fingerprint in known_fingerprints:
                duplicates += 1
                continue
            try:
                with transaction.atomic():
                    organization = Organization.objects.filter(name__iexact=item.company.strip()).first()
                    if organization is None:
                        organization = Organization.objects.create(name=item.company.strip(), location=item.location.strip())
                    missing = "\n".join(f"Unknown: {fact}" for fact in item.missing_information)
                    fit_summary = item.fit_summary.strip()
                    if missing:
                        fit_summary = f"{fit_summary}\n\nStill to verify:\n{missing}"
                    values = {
                        "organization": organization,
                        "title": item.title.strip(),
                        "kind": item.kind,
                        "location": item.location.strip(),
                        "job_description": item.description.strip(),
                        "match_score": item.match_score,
                        "fit_summary": fit_summary,
                        "next_action": item.next_action.strip(),
                        "candidate_fee_required": item.candidate_fee_required,
                        "candidate_fee": item.candidate_fee.strip(),
                        "compensation": item.compensation.strip(),
                        "canonical_url": canonical_url,
                        "fingerprint": fingerprint,
                        "verification_status": Opportunity.VerificationStatus.PENDING,
                        "verified_at": None,
                    }
                    if item.candidate_fee_required:
                        # Save it (marked unsuitable) instead of discarding it, so it stays out of
                        # future known-roles context and Robert never re-spends search budget on it.
                        values["verification_status"] = Opportunity.VerificationStatus.UNSUITABLE
                        values["verified_at"] = timezone.now()
                        values["next_action"] = "Not suitable — candidate fee required"
                    Opportunity.objects.create(
                        campaign=campaign,
                        source_url=source_url,
                        status=Opportunity.Status.DISCOVERED,
                        **values,
                    )
            except Exception:
                logger.exception(
                    "Skipped one discovered opportunity (%r at %r) after a save error", item.title, item.company,
                )
                continue
            known_urls.add(canonical_url)
            known_fingerprints.add(fingerprint)
            if item.candidate_fee_required:
                fee_blocked += 1
            else:
                added += 1
        next_sequence = (SearchCycle.objects.filter(campaign=campaign).order_by("-sequence").values_list("sequence", flat=True).first() or 0) + 1
        SearchCycle.objects.create(
            campaign=campaign,
            sequence=next_sequence,
            strategy=batch.search_strategy.strip(),
            queries=batch.queries_used,
            sources=batch.sources_searched,
            found_count=len(batch.opportunities),
            added_count=added,
            duplicate_count=duplicates,
            fee_blocked_count=fee_blocked,
        )
        ChatMessage.objects.create(
            scope=ChatMessage.Scope.GENERAL,
            role=ChatMessage.Role.ASSISTANT,
            content=f"Autonomous search complete. {batch.summary} I added {added}, blocked {duplicates} duplicates and excluded {fee_blocked} fee-charging programs. Nothing was applied to.",
        )
        messages.success(request, f"Robert added {added} new possibilities, blocked {duplicates} duplicates and excluded {fee_blocked} fee-charging programs.")
    except AIUnavailable as error:
        messages.error(request, str(error))
    except Exception:
        logger.exception("Discovery run failed for campaign %s", campaign.id)
        messages.error(request, "Robert’s web search was interrupted. Nothing was added incorrectly; please try again.")
    return redirect("dashboard")


@require_POST
def qualify_discoveries(request):
    campaign = SearchCampaign.objects.filter(is_active=True).first()
    if not campaign:
        messages.error(request, "Create and activate a search campaign before Robert researches discoveries.")
        return redirect("campaign-list")
    profile = CandidateProfile.objects.filter(pk=1).first()
    if not profile or not (profile.structured_profile or profile.profile_draft.strip()):
        messages.error(request, "Finish a basic profile first so Robert can compare qualifications truthfully.")
        return redirect("profile")
    opportunity_query = Opportunity.objects.select_related("organization").filter(campaign=campaign)
    requested_ids = [value for value in request.POST.getlist("opportunity_ids") if value.isdigit()]
    if requested_ids:
        opportunity_query = opportunity_query.filter(pk__in=requested_ids)
    else:
        opportunity_query = opportunity_query.filter(_incomplete_research_filter())
    opportunities = list(opportunity_query.order_by("-match_score", "-created_at")[:8])
    if not opportunities:
        messages.info(request, "There are no new discoveries waiting for research.")
        return redirect("dashboard")

    opportunity_map = {item.id: item for item in opportunities}
    try:
        batch = qualify_opportunities(campaign, profile, opportunities)
        researched = 0
        for report in batch.reports:
            opportunity = opportunity_map.get(report.opportunity_id)
            if opportunity is None:
                continue
            try:
                with transaction.atomic():
                    website = report.company_website.strip()
                    parsed_website = urlparse(website)
                    if parsed_website.scheme in {"http", "https"} and parsed_website.netloc:
                        opportunity.organization.website = website
                    logo_url = report.company_logo_url.strip()
                    if _looks_like_logo_image(logo_url):
                        opportunity.organization.logo_url = logo_url
                    if report.company_location.strip():
                        opportunity.organization.location = report.company_location.strip()
                    opportunity.organization.save(update_fields=["website", "logo_url", "location", "updated_at"])

                    safe_sources = []
                    for source in report.sources:
                        parsed_source = urlparse(source.url.strip())
                        if parsed_source.scheme in {"http", "https"} and parsed_source.netloc:
                            safe_sources.append({"title": source.title.strip(), "url": source.url.strip()})
                    opportunity.verification_status = (
                        Opportunity.VerificationStatus.UNSUITABLE
                        if report.candidate_fee_required else report.verdict
                    )
                    opportunity.company_description = report.company_description.strip()
                    opportunity.company_location = report.company_location.strip()
                    opportunity.company_size = report.company_size.strip()
                    opportunity.company_country = report.company_country.strip()
                    opportunity.company_industry = report.company_industry.strip()
                    opportunity.company_reputation = report.company_reputation.strip()
                    opportunity.cv_value = report.cv_value.strip()
                    opportunity.international_environment = report.international_environment.strip()
                    opportunity.growth_outlook = report.growth_outlook.strip()
                    opportunity.work_culture = report.work_culture.strip()
                    opportunity.location = report.internship_location.strip() or opportunity.location
                    opportunity.internship_dates = report.internship_dates.strip()
                    opportunity.internship_start_date = report.internship_start_date_iso
                    opportunity.internship_end_date = report.internship_end_date_iso
                    opportunity.minimum_duration = report.minimum_duration.strip()
                    opportunity.application_deadline_text = report.application_deadline.strip()
                    opportunity.deadline = report.application_deadline_iso
                    opportunity.responsibilities = report.responsibilities
                    opportunity.what_you_would_do = report.what_you_would_do.strip()
                    opportunity.what_company_needs = report.what_company_needs.strip()
                    opportunity.candidate_fee_required = report.candidate_fee_required
                    opportunity.candidate_fee = report.candidate_fee.strip()
                    opportunity.compensation = report.compensation.strip()
                    opportunity.work_arrangement = report.work_arrangement.strip()
                    opportunity.japanese_requirement = report.japanese_requirement.strip()
                    opportunity.posting_language = report.posting_language
                    opportunity.posting_language_note = report.posting_language_note.strip()
                    opportunity.japanese_only_inferred = report.japanese_only_inferred
                    opportunity.visa_support = report.visa_support.strip()
                    opportunity.thesis_compatibility = report.thesis_compatibility.strip()
                    opportunity.job_description = report.role_summary.strip() or opportunity.job_description
                    opportunity.match_score = report.match_score
                    opportunity.fit_summary = report.fit_summary.strip()
                    opportunity.requirements_assessment = [
                        item.model_dump() for item in report.requirements
                        if _is_concrete_qualification(item.requirement)
                    ]
                    opportunity.research_sources = safe_sources
                    opportunity.research_summary = batch.summary.strip()
                    if not opportunity.next_action_is_manual:
                        opportunity.next_action = report.next_action.strip()
                    opportunity.verified_at = timezone.now()
                    if opportunity.verification_status == Opportunity.VerificationStatus.QUALIFIED:
                        opportunity.status = Opportunity.Status.QUALIFIED
                    opportunity.save(update_fields=[
                        "verification_status", "company_description", "company_location", "company_size",
                        "company_country", "company_industry",
                        "company_reputation", "cv_value", "international_environment", "growth_outlook", "work_culture",
                        "location", "internship_dates", "internship_start_date", "internship_end_date",
                        "minimum_duration", "work_arrangement", "japanese_requirement",
                        "posting_language", "posting_language_note", "japanese_only_inferred",
                        "application_deadline_text", "deadline", "responsibilities",
                        "what_you_would_do", "what_company_needs", "candidate_fee_required",
                        "candidate_fee", "compensation",
                        "visa_support", "thesis_compatibility", "job_description", "match_score",
                        "fit_summary", "requirements_assessment", "research_sources", "research_summary",
                        "next_action", "verified_at", "status", "updated_at",
                    ])
            except Exception:
                logger.exception(
                    "Skipped research report for opportunity %s after a save error", report.opportunity_id,
                )
                continue
            researched += 1
        ChatMessage.objects.create(
            scope=ChatMessage.Scope.GENERAL,
            role=ChatMessage.Role.ASSISTANT,
            content=f"I deeply researched {researched} discoveries. {batch.summary} I did not apply or contact anyone.",
        )
        messages.success(request, f"Robert finished researching {researched} opportunities. Open any row to see its practical report.")
    except AIUnavailable as error:
        messages.error(request, str(error))
    except Exception:
        logger.exception("Qualification run failed for campaign %s", campaign.id)
        messages.error(request, "Robert’s verification run was interrupted. Existing information is safe; please try again.")
    return redirect("dashboard")


def campaign_list(request):
    # Older data can have several campaigns flagged active. Mark only the one the
    # dashboard and Robert actually use, so every other card stays switchable.
    return render(request, "tracker/campaign_list.html", {
        "campaigns": SearchCampaign.objects.annotate(opportunity_count=Count("opportunities")),
        "active_campaign": SearchCampaign.objects.filter(is_active=True).first(),
    })


@require_POST
def campaign_activate(request, campaign_id):
    """Switch to one job-hunt sheet. Exactly one campaign is active at a time, so
    Robert and the Applications list can never disagree about which search is in use."""
    campaign = get_object_or_404(SearchCampaign, pk=campaign_id)
    with transaction.atomic():
        SearchCampaign.objects.exclude(pk=campaign.pk).filter(is_active=True).update(
            is_active=False, updated_at=timezone.now(),
        )
        SearchCampaign.objects.filter(pk=campaign.pk).update(is_active=True, updated_at=timezone.now())
    messages.success(request, f'Now working on "{campaign.name}". The Applications list shows only this search.')
    return redirect("dashboard")


def campaign_create(request):
    form = CampaignPromptForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        campaign = form.save()
        user_text = form.cleaned_data["description"].strip()
        if is_configured():
            try:
                turn = campaign_reply(campaign, user_text)
                _apply_campaign_turn(campaign, turn)
                assistant_text = turn.reply
            except Exception:
                assistant_text = "I saved that safely, but I could not reach the AI service. Try Send again in a moment."
        else:
            assistant_text = "I saved your starting idea. Connect OpenAI once, then I can ask focused follow-up questions and build the editable settings with you."
        ChatMessage.objects.create(
            scope=ChatMessage.Scope.CAMPAIGN, role=ChatMessage.Role.USER,
            campaign=campaign, content=user_text,
        )
        ChatMessage.objects.create(
            scope=ChatMessage.Scope.CAMPAIGN, role=ChatMessage.Role.ASSISTANT,
            campaign=campaign, content=assistant_text,
        )
        return redirect("campaign-setup", campaign_id=campaign.id)
    return render(request, "tracker/campaign_prompt.html", {
        "form": form, "page_title": "Create a search campaign",
    })


def _apply_campaign_turn(campaign, turn):
    editable_fields = [
        "name", "goal", "locations", "start_date", "end_date", "desired_work",
        "avoid_work", "work_style", "company_preferences", "language_requirements",
        "visa_requirements", "university_requirements", "notes",
    ]
    changed = []
    for field in editable_fields:
        value = getattr(turn, field, None)
        if value is not None:
            setattr(campaign, field, value)
            changed.append(field)
    if turn.ready:
        campaign.setup_status = "ready"
        campaign.is_active = True
        changed.extend(["setup_status", "is_active"])
    if changed:
        campaign.save(update_fields=list(dict.fromkeys(changed)) + ["updated_at"])


def campaign_setup(request, campaign_id):
    campaign = get_object_or_404(SearchCampaign, id=campaign_id)
    if request.method == "POST":
        user_text = request.POST.get("message", "").strip()
        if user_text:
            try:
                turn = campaign_reply(campaign, user_text)
                assistant_text = turn.reply
                _apply_campaign_turn(campaign, turn)
            except AIUnavailable as error:
                assistant_text = str(error)
            except Exception:
                assistant_text = "Something interrupted that answer. Your message is saved; please try again."
            ChatMessage.objects.create(
                scope=ChatMessage.Scope.CAMPAIGN, role=ChatMessage.Role.USER,
                campaign=campaign, content=user_text,
            )
            ChatMessage.objects.create(
                scope=ChatMessage.Scope.CAMPAIGN, role=ChatMessage.Role.ASSISTANT,
                campaign=campaign, content=assistant_text,
            )
            return redirect("campaign-setup", campaign_id=campaign.id)
        messages.error(request, "Type or dictate a message first.")
    return render(request, "tracker/campaign_setup.html", {
        "campaign": campaign,
        "conversation": campaign.chat_messages.all(),
        "ai_configured": is_configured(),
    })


def campaign_create_advanced(request):
    form = SearchCampaignForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        campaign = form.save()
        messages.success(request, f'Campaign "{campaign.name}" was created.')
        return redirect("campaign-list")
    return render(request, "tracker/campaign_form.html", {
        "form": form, "page_title": "Advanced campaign setup",
    })


def campaign_edit(request, campaign_id):
    campaign = get_object_or_404(SearchCampaign, id=campaign_id)
    form = SearchCampaignForm(request.POST or None, instance=campaign)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'Campaign "{campaign.name}" was updated.')
        return redirect("campaign-list")
    return render(request, "tracker/campaign_form.html", {
        "form": form, "page_title": "Edit search campaign", "campaign": campaign,
    })


def opportunity_create(request):
    form = OpportunityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        opportunity = form.save()
        messages.success(request, f'"{opportunity.title}" at {opportunity.organization.name} was added.')
        return redirect("dashboard")
    return render(request, "tracker/opportunity_form.html", {
        "form": form, "page_title": "Add an opportunity",
    })


def opportunity_edit(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, id=opportunity_id)
    form = OpportunityForm(request.POST or None, instance=opportunity)
    if request.method == "POST" and form.is_valid():
        opportunity = form.save()
        messages.success(request, f'"{opportunity.title}" was updated.')
        return redirect("dashboard")
    return render(request, "tracker/opportunity_form.html", {
        "form": form, "page_title": "Edit opportunity", "opportunity": opportunity,
    })


def profile(request):
    candidate, _ = CandidateProfile.objects.get_or_create(pk=1)
    profile_form = ProfileSourceNotesForm(instance=candidate)
    linkedin_form = LinkedInSourceForm(instance=candidate)
    document_form = ProfileDocumentUploadForm()

    if request.method == "POST" and request.POST.get("action") == "save_profile":
        profile_form = ProfileSourceNotesForm(request.POST, instance=candidate)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Your profile description was saved.")
            return redirect("profile")

    if request.method == "POST" and request.POST.get("action") == "save_linkedin":
        linkedin_form = LinkedInSourceForm(request.POST, instance=candidate)
        if linkedin_form.is_valid():
            linkedin_form.save()
            if candidate.linkedin_source_text.strip():
                messages.success(request, "LinkedIn evidence was saved. Ask Robert to compare all sources below.")
            else:
                messages.info(request, "LinkedIn link saved. Paste its profile text or upload the LinkedIn PDF before comparison; LinkedIn blocks reliable automatic reading.")
            return redirect("profile")

    if request.method == "POST" and request.POST.get("action") == "upload_document":
        document_form = ProfileDocumentUploadForm(request.POST, request.FILES)
        if document_form.is_valid():
            group_label = document_form.cleaned_data.get("label", "").strip()
            files = document_form.cleaned_data["files"]
            for uploaded_file in files:
                file_label = Path(uploaded_file.name).stem.replace("_", " ").replace("-", " ").title()
                label = f"{group_label}: {file_label}" if group_label else file_label
                ProfileDocument.objects.create(profile=candidate, label=label, file=uploaded_file)
            messages.success(request, f"{len(files)} document(s) uploaded locally.")
            return redirect("profile")

    if request.method == "POST" and request.POST.get("action") == "analyze_documents":
        documents = list(candidate.documents.all())
        if not documents and not candidate.linkedin_source_text.strip():
            messages.error(request, "Add a document or paste LinkedIn profile text before asking Robert to compare your sources.")
            return redirect("profile")
        try:
            result = analyze_profile_documents(
                documents,
                "\n\n".join(filter(None, [candidate.profile_draft, candidate.long_description])),
                candidate.linkedin_source_text,
            )
            candidate.document_profile_proposal = result.to_profile_text()
            candidate.document_structured_proposal = result.profile.model_dump()
            candidate.document_evidence = [item.model_dump() for item in result.evidence]
            candidate.document_questions = [result.important_question] if result.important_question else []
            candidate.document_analysis_status = CandidateProfile.AnalysisStatus.READY
            candidate.document_analysis_error = ""
            candidate.document_analyzed_at = timezone.now()
            candidate.save(update_fields=[
                "document_profile_proposal", "document_structured_proposal", "document_evidence", "document_questions",
                "document_analysis_status", "document_analysis_error", "document_analyzed_at", "updated_at",
            ])
            ChatMessage.objects.create(
                scope=ChatMessage.Scope.PROFILE,
                role=ChatMessage.Role.ASSISTANT,
                content=(
                    result.summary
                    + " Review my proposed profile below. Nothing has been accepted automatically."
                    + (f" One important question: {result.important_question}" if result.important_question else "")
                ),
            )
            messages.success(request, "Robert finished reading the documents. Review the proposal before accepting it.")
        except AIUnavailable as error:
            messages.error(request, str(error))
        except Exception:
            candidate.document_analysis_status = CandidateProfile.AnalysisStatus.ERROR
            candidate.document_analysis_error = "Robert could not analyze the documents. The originals are still safe on this Mac."
            candidate.save(update_fields=["document_analysis_status", "document_analysis_error", "updated_at"])
            messages.error(request, candidate.document_analysis_error)
        return redirect("profile")

    if request.method == "POST" and request.POST.get("action") == "accept_document_profile":
        proposal = candidate.document_profile_proposal.strip()
        if proposal:
            update_fields = [
                "document_profile_proposal", "profile_draft", "structured_profile",
                "full_name", "headline", "updated_at",
            ]
            if candidate.profile_draft.strip() and not candidate.long_description.strip():
                candidate.long_description = candidate.profile_draft.strip()
                update_fields.append("long_description")
            candidate.document_profile_proposal = proposal
            candidate.profile_draft = proposal
            candidate.structured_profile = candidate.document_structured_proposal
            candidate.full_name = candidate.structured_profile.get("name", candidate.full_name)
            candidate.headline = candidate.structured_profile.get("headline", candidate.headline)
            candidate.save(update_fields=update_fields)
            messages.success(request, "The reviewed document profile is now your editable source of truth.")
        else:
            messages.error(request, "The proposed profile cannot be empty.")
        return redirect("profile")

    if request.method == "POST" and request.POST.get("action") == "interview_answer":
        answer = request.POST.get("answer", "").strip()
        if answer:
            current_profile = "\n\n".join(filter(None, [candidate.profile_draft, candidate.long_description]))
            try:
                turn = profile_reply(answer, current_profile)
                assistant_text = turn.reply
                candidate.profile_draft = turn.revised_profile
            except AIUnavailable as error:
                assistant_text = str(error) + " Your answer was still added to the editable profile."
                prefix = f"{candidate.profile_draft.rstrip()}\n\n" if candidate.profile_draft.strip() else ""
                candidate.profile_draft = f"{prefix}Interview note\n{answer}"
            except Exception:
                assistant_text = "I saved your answer, but the AI response was interrupted. Please try another message."
                prefix = f"{candidate.profile_draft.rstrip()}\n\n" if candidate.profile_draft.strip() else ""
                candidate.profile_draft = f"{prefix}Interview note\n{answer}"
            if answer not in candidate.long_description:
                note_prefix = f"{candidate.long_description.rstrip()}\n\n" if candidate.long_description.strip() else ""
                candidate.long_description = f"{note_prefix}Robert interview answer\n{answer}"
            candidate.save(update_fields=["profile_draft", "long_description", "updated_at"])
            ChatMessage.objects.create(scope=ChatMessage.Scope.PROFILE, role=ChatMessage.Role.USER, content=answer)
            ChatMessage.objects.create(scope=ChatMessage.Scope.PROFILE, role=ChatMessage.Role.ASSISTANT, content=assistant_text)
            messages.success(request, "Your answer was saved and the live profile was updated.")
            return redirect("profile")
        messages.error(request, "Please answer the interview question before sending.")

    if not ChatMessage.objects.filter(scope=ChatMessage.Scope.PROFILE).exists():
        ChatMessage.objects.create(
            scope=ChatMessage.Scope.PROFILE,
            role=ChatMessage.Role.ASSISTANT,
            content="Let’s build a truthful profile I can use for every search and application. What are you studying, where, and what must your graduation internship include?",
        )
    conversation = ChatMessage.objects.filter(scope=ChatMessage.Scope.PROFILE)

    display_profile = (
        candidate.document_structured_proposal
        if candidate.document_analysis_status == CandidateProfile.AnalysisStatus.READY and candidate.document_structured_proposal
        else candidate.structured_profile
    )
    return render(request, "tracker/profile.html", {
        "candidate": candidate,
        "profile_form": profile_form,
        "linkedin_form": linkedin_form,
        "document_form": document_form,
        "conversation": conversation,
        "ai_configured": is_configured(),
        "display_profile": display_profile,
        "profile_is_proposal": bool(
            candidate.document_analysis_status == CandidateProfile.AnalysisStatus.READY
            and candidate.document_structured_proposal
        ),
    })


def inbox(request):
    if not SearchCampaign.objects.exists():
        messages.info(request, "Create a search campaign before adding opportunities.")
        return redirect("campaign-create")

    initial_campaign = SearchCampaign.objects.filter(is_active=True).first()
    form = QuickInboxForm(request.POST or None, request.FILES or None, initial={"campaign": initial_campaign})
    if request.method == "POST" and form.is_valid():
        item = form.save()
        if _start_inbox_analysis(item):
            messages.success(request, "Saved. Robert is researching it now; nothing is applied to or submitted.")
        else:
            messages.success(request, "Saved. Add the OpenAI key and restart to let Robert research it.")
        return redirect("inbox")

    items = list(
        InboxItem.objects.select_related("campaign", "opportunity", "opportunity__organization")
        .prefetch_related("attachments")[:50]
    )
    for item in items:
        item.card = _inbox_card(item)
    return render(request, "tracker/inbox.html", {
        "form": form,
        "items": items,
        "waiting_count": InboxItem.objects.filter(
            status__in=[InboxItem.Status.WAITING, InboxItem.Status.ANALYZING],
        ).count(),
        "is_analyzing": any(item.status == InboxItem.Status.ANALYZING for item in items),
    })


INBOX_VERDICT_LABELS = {
    Opportunity.VerificationStatus.QUALIFIED: ("Eligible", "good"),
    Opportunity.VerificationStatus.CLARIFY: ("Worth checking", "warn"),
    Opportunity.VerificationStatus.UNSUITABLE: ("Not suitable", "bad"),
    Opportunity.VerificationStatus.EXPIRED: ("Closed", "bad"),
    Opportunity.VerificationStatus.UNVERIFIED: ("Unverified", "muted"),
    Opportunity.VerificationStatus.PENDING: ("Not researched", "muted"),
}


def _inbox_card(item):
    """One compact, honest line per capture: what it is, whether it is worth your
    time, and the two or three facts that decide that. Everything else is noise."""
    if item.status == InboxItem.Status.ANALYZING:
        return {"label": "Researching…", "tone": "busy", "heading": _inbox_capture_title(item), "facts": []}
    if item.status != InboxItem.Status.PROCESSED or not item.opportunity:
        return {"label": "Not a vacancy", "tone": "muted", "heading": _inbox_capture_title(item), "facts": []}

    opportunity = item.opportunity
    label, tone = INBOX_VERDICT_LABELS.get(opportunity.verification_status, ("Saved", "muted"))
    facts = [fact for fact in [
        opportunity.location,
        opportunity.internship_dates or opportunity.minimum_duration,
        f"{opportunity.match_score}% match" if opportunity.match_score is not None else "",
        opportunity.compensation if opportunity.compensation.lower() not in {"", "not stated"} else "",
    ] if fact]
    return {
        "label": label,
        "tone": tone,
        "heading": f"{opportunity.organization.name} — {opportunity.title}",
        "logo_url": opportunity.organization.logo_url,
        "initial": opportunity.organization.name[:1].upper(),
        "facts": facts[:3],
    }


def _inbox_capture_title(item):
    if item.content.strip():
        return item.content.strip()[:90]
    if item.source_url:
        return item.source_url
    return "Uploaded files"


def _save_inbox_reading(item, campaign, analysis):
    """Store one reading. Returns the opportunity, or None when Robert could not
    establish a real employer, role and source and needs Francesco to say more."""
    note = _plain_text(analysis.note)
    source_url = _strip_tracking(analysis.source_url)
    parsed = urlparse(source_url)
    usable_link = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    if not analysis.is_opportunity or analysis.needs_more_information or not usable_link or not analysis.company.strip():
        InboxItem.objects.filter(pk=item.pk).update(
            status=InboxItem.Status.NEEDS_INPUT,
            analysis_note=note or "Robert could not establish the employer, the role or a real source link.",
            analyzed_at=timezone.now(),
        )
        return None

    canonical_url = _canonicalize_url(source_url)
    fingerprint = _opportunity_fingerprint(analysis.company, analysis.title, analysis.location)
    existing = Opportunity.objects.filter(campaign=campaign).filter(
        Q(canonical_url=canonical_url) | Q(fingerprint=fingerprint),
    ).first()
    if existing:
        InboxItem.objects.filter(pk=item.pk).update(
            status=InboxItem.Status.PROCESSED, opportunity=existing,
            analysis_note=f"Already saved as “{existing.title}”. Linked to the application you already have.",
            analyzed_at=timezone.now(),
        )
        return existing

    with transaction.atomic():
        organization = Organization.objects.filter(name__iexact=analysis.company.strip()).first()
        if organization is None:
            organization = Organization.objects.create(
                name=analysis.company.strip(), location=analysis.location.strip(),
            )
        missing = "\n".join(f"Unknown: {fact}" for fact in analysis.missing_information)
        fit_summary = _plain_text(analysis.fit_summary)
        if missing:
            fit_summary = f"{fit_summary}\n\nStill to verify:\n{missing}"
        opportunity = Opportunity.objects.create(
            # Robert's reading travels with the role, so a caveat raised while
            # reading the inbox is not lost the moment you open the application.
            notes=f"From your job inbox:\n{note}" if note else "",
            campaign=campaign,
            organization=organization,
            title=analysis.title.strip(),
            kind=analysis.kind,
            location=analysis.location.strip(),
            source_url=source_url,
            canonical_url=canonical_url,
            fingerprint=fingerprint,
            job_description=analysis.description.strip(),
            match_score=analysis.match_score,
            fit_summary=fit_summary,
            next_action=analysis.next_action.strip(),
            candidate_fee_required=analysis.candidate_fee_required,
            candidate_fee=analysis.candidate_fee.strip(),
            compensation=analysis.compensation.strip(),
            status=Opportunity.Status.DISCOVERED,
            verification_status=(
                Opportunity.VerificationStatus.UNSUITABLE if analysis.candidate_fee_required
                else Opportunity.VerificationStatus.PENDING
            ),
            verified_at=timezone.now() if analysis.candidate_fee_required else None,
        )
        InboxItem.objects.filter(pk=item.pk).update(
            status=InboxItem.Status.PROCESSED, opportunity=opportunity,
            analysis_note=note, analyzed_at=timezone.now(),
        )
    return opportunity


def _run_inbox_analysis(item_id):
    """Read one capture, then research it properly before it lands in the list.

    Runs in a background thread because reading plus full research takes most of
    a minute, and Francesco should not be staring at a frozen page for it.
    """
    from django.test import Client

    close_old_connections()
    try:
        item = InboxItem.objects.prefetch_related("attachments").get(pk=item_id)
        campaign = SearchCampaign.objects.filter(is_active=True).first()
        profile = CandidateProfile.objects.filter(pk=1).first()
        if not campaign or not profile:
            InboxItem.objects.filter(pk=item_id).update(
                status=InboxItem.Status.NEEDS_INPUT,
                analysis_note="Activate a campaign and finish your profile, then try again.",
            )
            return
        opportunity = _save_inbox_reading(item, campaign, _do_analyze_inbox_item(campaign, profile, item))
        if opportunity and not opportunity.candidate_fee_required:
            # Same research every discovery gets, so nothing lands half-known.
            Client(HTTP_HOST=_internal_host()).post(
                reverse("qualify-discoveries"), {"opportunity_ids": [opportunity.id]},
            )
    except AIUnavailable as error:
        InboxItem.objects.filter(pk=item_id).update(
            status=InboxItem.Status.NEEDS_INPUT, analysis_note=str(error), analyzed_at=timezone.now(),
        )
    except Exception:
        logger.exception("Inbox analysis failed for item %s", item_id)
        InboxItem.objects.filter(pk=item_id).update(
            status=InboxItem.Status.NEEDS_INPUT, analyzed_at=timezone.now(),
            analysis_note="Robert could not finish reading this one. Nothing was changed; press Analyse again.",
        )
    finally:
        close_old_connections()


def _do_analyze_inbox_item(campaign, profile, item):
    """Indirection so tests can patch the AI call without patching the runner."""
    return analyze_inbox_item(campaign, profile, item)


def _start_inbox_analysis(item):
    """Mark the capture as being worked on and hand it to a background thread."""
    if not is_configured():
        return False
    InboxItem.objects.filter(pk=item.pk).update(
        status=InboxItem.Status.ANALYZING, analysis_note="", analyzed_at=None,
    )
    Thread(target=_run_inbox_analysis, args=(item.pk,), daemon=True).start()
    return True


@require_POST
def inbox_analyze(request, item_id):
    """Re-read one capture. Saving already starts this automatically."""
    item = get_object_or_404(InboxItem, pk=item_id)
    if not SearchCampaign.objects.filter(is_active=True).exists():
        messages.error(request, "Activate a search campaign before Robert analyses the inbox.")
        return redirect("campaign-list")
    profile = CandidateProfile.objects.filter(pk=1).first()
    if not profile or not (profile.structured_profile or profile.profile_draft.strip()):
        messages.error(request, "Finish a basic profile first so Robert can judge whether this fits you.")
        return redirect("profile")
    if not _start_inbox_analysis(item):
        messages.error(request, "Robert is not connected yet. Add the OpenAI key and restart.")
    return redirect("inbox")


@require_POST
def robert_send(request):
    user_text = request.POST.get("message", "").strip()
    next_url = request.POST.get("next", "")
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = reverse("dashboard")
    if not user_text:
        messages.error(request, "Type or dictate a message for Robert first.")
        return redirect(next_url)
    try:
        assistant_text = robert_reply(user_text)
    except AIUnavailable as error:
        assistant_text = str(error)
    except Exception:
        assistant_text = "I could not reach the AI service just now. Your question is saved; try again shortly."
    ChatMessage.objects.create(scope=ChatMessage.Scope.GENERAL, role=ChatMessage.Role.USER, content=user_text)
    ChatMessage.objects.create(scope=ChatMessage.Scope.GENERAL, role=ChatMessage.Role.ASSISTANT, content=assistant_text)
    return redirect(next_url + ("&" if "?" in next_url else "?") + "robert=open")


@require_POST
def transcribe_audio(request):
    audio = request.FILES.get("audio")
    if not audio:
        return JsonResponse({"error": "No recording was received."}, status=400)
    if audio.size > 15 * 1024 * 1024:
        return JsonResponse({"error": "That recording is too large. Keep each dictation under five minutes."}, status=400)
    try:
        text = transcribe(audio, request.POST.get("duration_seconds", 0))
        return JsonResponse({"text": text})
    except AIUnavailable as error:
        return JsonResponse({"error": str(error)}, status=503)
    except Exception:
        return JsonResponse({"error": "Transcription failed. Check the AI connection and try again."}, status=502)
