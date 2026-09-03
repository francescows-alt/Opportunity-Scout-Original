from pathlib import Path

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    CandidateProfileForm,
    CampaignPromptForm,
    OpportunityForm,
    ProfileDocumentUploadForm,
    QuickInboxForm,
    SearchCampaignForm,
)
from .models import CandidateProfile, InboxItem, Opportunity, ProfileDocument, ProfileInterviewAnswer, SearchCampaign


PROFILE_QUESTIONS = [
    ("education", "Education", "What are you studying, where are you studying, and when do you expect to graduate?"),
    ("experience", "Experience", "Tell me about jobs, internships, volunteering, university projects, or businesses you have worked on."),
    ("achievements", "Achievements", "What results or achievements are you proud of? Numbers and concrete examples are especially useful."),
    ("skills", "Skills and languages", "Which tools, business skills, technical skills, and languages can you genuinely use?"),
    ("motivation", "Motivation", "What kind of work makes you curious or energized, and what work would you rather avoid?"),
    ("constraints", "Practical constraints", "What dates, locations, visa needs, university rules, working hours, or other limits matter?"),
    ("story", "Personal story", "What else should a company understand about you that may not appear on your CV?"),
]


def home(request):
    return redirect("dashboard")


def dashboard(request):
    opportunities = Opportunity.objects.select_related("campaign", "organization")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if query:
        opportunities = opportunities.filter(
            Q(organization__name__icontains=query)
            | Q(title__icontains=query)
            | Q(location__icontains=query)
        )
    if status:
        opportunities = opportunities.filter(status=status)

    paginator = Paginator(opportunities, 25)
    page = paginator.get_page(request.GET.get("page"))
    selected = None
    selected_id = request.GET.get("selected")
    if selected_id:
        selected = opportunities.filter(id=selected_id).first()
    if selected is None and page.object_list:
        selected = page.object_list[0]

    all_opportunities = Opportunity.objects.all()
    context = {
        "page": page,
        "selected": selected,
        "query": query,
        "current_status": status,
        "statuses": Opportunity.Status.choices,
        "tracked_count": all_opportunities.count(),
        "draft_count": all_opportunities.filter(status=Opportunity.Status.DRAFT_READY).count(),
        "sent_count": all_opportunities.filter(submitted_on__isnull=False).count(),
        "action_count": all_opportunities.exclude(next_action="").exclude(
            status__in=[Opportunity.Status.REJECTED, Opportunity.Status.OFFER]
        ).count(),
        "active_campaign": SearchCampaign.objects.filter(is_active=True).first(),
    }
    return render(request, "tracker/dashboard.html", context)


def campaign_list(request):
    return render(request, "tracker/campaign_list.html", {"campaigns": SearchCampaign.objects.all()})


def campaign_create(request):
    form = CampaignPromptForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        campaign = form.save()
        messages.success(request, f'Campaign request "{campaign.name}" was saved for AI setup.')
        return redirect("campaign-list")
    return render(request, "tracker/campaign_prompt.html", {
        "form": form, "page_title": "Create a search campaign",
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
    profile_form = CandidateProfileForm(instance=candidate)
    document_form = ProfileDocumentUploadForm()

    if request.method == "POST" and request.POST.get("action") == "save_profile":
        profile_form = CandidateProfileForm(request.POST, instance=candidate)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Your profile description was saved.")
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

    if request.method == "POST" and request.POST.get("action") == "interview_answer":
        question_key = request.POST.get("question_key", "")
        answer = request.POST.get("answer", "").strip()
        question_data = next((item for item in PROFILE_QUESTIONS if item[0] == question_key), None)
        if question_data and answer:
            position = next(index for index, item in enumerate(PROFILE_QUESTIONS) if item[0] == question_key)
            _, section_title, question = question_data
            _, created = ProfileInterviewAnswer.objects.update_or_create(
                profile=candidate,
                question_key=question_key,
                defaults={
                    "question": question,
                    "section_title": section_title,
                    "answer": answer,
                    "position": position,
                },
            )
            if created:
                prefix = f"{candidate.profile_draft.rstrip()}\n\n" if candidate.profile_draft.strip() else ""
                candidate.profile_draft = f"{prefix}{section_title}\n{answer}"
                candidate.save(update_fields=["profile_draft", "updated_at"])
            messages.success(request, "Answer saved and added to your live profile draft.")
            return redirect("profile")
        messages.error(request, "Please answer the interview question before sending.")

    answers = {answer.question_key: answer for answer in candidate.interview_answers.all()}
    conversation = []
    current_question = None
    for key, section_title, question in PROFILE_QUESTIONS:
        conversation.append({"role": "assistant", "text": question})
        if key in answers:
            conversation.append({"role": "user", "text": answers[key].answer})
        else:
            current_question = {"key": key, "section_title": section_title, "text": question}
            break

    return render(request, "tracker/profile.html", {
        "candidate": candidate,
        "profile_form": profile_form,
        "document_form": document_form,
        "conversation": conversation,
        "current_question": current_question,
        "answered_count": len(answers),
        "question_count": len(PROFILE_QUESTIONS),
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
