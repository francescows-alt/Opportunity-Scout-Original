import hashlib
from pathlib import Path
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .ai import AIUnavailable, analyze_profile_documents, campaign_reply, is_configured, profile_reply, qualify_opportunities, research_internships, robert_reply, transcribe

from .forms import (
    CampaignPromptForm,
    OpportunityForm,
    LinkedInSourceForm,
    ProfileDocumentUploadForm,
    ProfileSourceNotesForm,
    QuickInboxForm,
    SearchCampaignForm,
)
from .models import CandidateProfile, ChatMessage, InboxItem, Opportunity, Organization, ProfileDocument, SearchCampaign, SearchCycle


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


def _normalized_words(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _opportunity_fingerprint(company, title, location):
    identity = "|".join((_normalized_words(company), _normalized_words(title), _normalized_words(location)))
    return hashlib.sha256(identity.encode()).hexdigest()


def home(request):
    return redirect("dashboard")


def dashboard(request):
    opportunities = Opportunity.objects.select_related("campaign", "organization")
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
    incomplete_research = (
        Q(verification_status=Opportunity.VerificationStatus.PENDING)
        | Q(company_country="")
        | Q(company_industry="")
        | Q(what_you_would_do="")
        | Q(what_company_needs="")
        | Q(candidate_fee="")
        | Q(compensation="")
    )
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

    all_opportunities = Opportunity.objects.all()
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
        "active_campaign": SearchCampaign.objects.filter(is_active=True).first(),
        "ai_configured": is_configured(),
        "research_needed_count": research_needed_count,
        "research_batch_count": min(research_needed_count, 8),
        "serious_count": all_opportunities.filter(
            verification_status=Opportunity.VerificationStatus.QUALIFIED,
        ).count(),
        "clarify_count": all_opportunities.filter(
            verification_status=Opportunity.VerificationStatus.CLARIFY,
        ).count(),
        "favorites_count": all_opportunities.filter(is_favorite=True).count(),
    }
    return render(request, "tracker/dashboard.html", context)


@require_POST
def toggle_favorite(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, pk=opportunity_id)
    opportunity.is_favorite = not opportunity.is_favorite
    opportunity.save(update_fields=["is_favorite", "updated_at"])
    return redirect(f"{reverse('dashboard')}?selected={opportunity.id}")


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
            if item.candidate_fee_required:
                fee_blocked += 1
                continue
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
            Opportunity.objects.create(
                campaign=campaign,
                source_url=source_url,
                status=Opportunity.Status.DISCOVERED,
                **values,
            )
            known_urls.add(canonical_url)
            known_fingerprints.add(fingerprint)
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
    opportunities = list(
        Opportunity.objects.select_related("organization")
        .filter(campaign=campaign)
        .filter(
            Q(verification_status=Opportunity.VerificationStatus.PENDING)
            | Q(company_country="")
            | Q(company_industry="")
            | Q(what_you_would_do="")
            | Q(what_company_needs="")
            | Q(candidate_fee="")
            | Q(compensation="")
        )
        .order_by("-match_score", "-created_at")[:8]
    )
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
            website = report.company_website.strip()
            parsed_website = urlparse(website)
            if parsed_website.scheme in {"http", "https"} and parsed_website.netloc:
                opportunity.organization.website = website
            logo_url = report.company_logo_url.strip()
            parsed_logo = urlparse(logo_url)
            if parsed_logo.scheme in {"http", "https"} and parsed_logo.netloc:
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
            opportunity.application_deadline_text = report.application_deadline.strip()
            opportunity.responsibilities = report.responsibilities
            opportunity.what_you_would_do = report.what_you_would_do.strip()
            opportunity.what_company_needs = report.what_company_needs.strip()
            opportunity.candidate_fee_required = report.candidate_fee_required
            opportunity.candidate_fee = report.candidate_fee.strip()
            opportunity.compensation = report.compensation.strip()
            opportunity.work_arrangement = report.work_arrangement.strip()
            opportunity.japanese_requirement = report.japanese_requirement.strip()
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
            opportunity.next_action = report.next_action.strip()
            opportunity.verified_at = timezone.now()
            if opportunity.verification_status == Opportunity.VerificationStatus.QUALIFIED:
                opportunity.status = Opportunity.Status.QUALIFIED
            opportunity.save(update_fields=[
                "verification_status", "company_description", "company_location", "company_size",
                "company_country", "company_industry",
                "company_reputation", "cv_value", "international_environment", "growth_outlook", "work_culture",
                "location", "internship_dates", "work_arrangement", "japanese_requirement",
                "application_deadline_text", "responsibilities",
                "what_you_would_do", "what_company_needs", "candidate_fee_required",
                "candidate_fee", "compensation",
                "visa_support", "thesis_compatibility", "job_description", "match_score",
                "fit_summary", "requirements_assessment", "research_sources", "research_summary",
                "next_action", "verified_at", "status", "updated_at",
            ])
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
        messages.error(request, "Robert’s verification run was interrupted. Existing information is safe; please try again.")
    return redirect("dashboard")


def campaign_list(request):
    return render(request, "tracker/campaign_list.html", {"campaigns": SearchCampaign.objects.all()})


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
        form.save()
        messages.success(request, "Saved to the inbox. It is waiting for AI analysis; nothing was invented or submitted.")
        return redirect("inbox")

    return render(request, "tracker/inbox.html", {
        "form": form,
        "items": InboxItem.objects.select_related("campaign", "opportunity").prefetch_related("attachments")[:50],
        "waiting_count": InboxItem.objects.filter(status=InboxItem.Status.WAITING).count(),
    })


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
