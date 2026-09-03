from django.db import models


class SearchCampaign(models.Model):
    """An editable description of one job or internship search."""

    name = models.CharField(max_length=120)
    goal = models.CharField(
        max_length=160,
        help_text="For example: graduation internship or first full-time job.",
    )
    locations = models.CharField(
        max_length=240,
        blank=True,
        help_text="Countries, cities, or remote locations you want to consider.",
    )
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    desired_work = models.TextField(
        blank=True,
        help_text="Loose preferences, not automatic rejection rules.",
    )
    avoid_work = models.TextField(
        blank=True,
        help_text="Work you usually want to avoid, unless there is a strong reason.",
    )
    work_style = models.TextField(
        blank=True,
        help_text="For example: hybrid, reasonable hours, or time for a thesis.",
    )
    company_preferences = models.TextField(
        blank=True,
        help_text="Useful signals such as learning, responsibility, reputation, or CV value.",
    )
    language_requirements = models.TextField(blank=True)
    visa_requirements = models.TextField(blank=True)
    university_requirements = models.TextField(
        blank=True,
        help_text="Rules to verify with your university. These can be changed later.",
    )
    notes = models.TextField(blank=True)
    natural_language_brief = models.TextField(
        blank=True,
        help_text="The original request used to create or update this campaign.",
    )
    setup_status = models.CharField(
        max_length=24,
        choices=[("ready", "Ready"), ("waiting_ai", "Waiting for AI setup")],
        default="ready",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Active campaigns appear first on the dashboard.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-updated_at"]

    def __str__(self):
        return self.name


class CandidateProfile(models.Model):
    class AnalysisStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not analyzed"
        READY = "ready", "Ready for review"
        ERROR = "error", "Analysis needs attention"

    full_name = models.CharField(max_length=160, blank=True)
    headline = models.CharField(
        max_length=240,
        blank=True,
        help_text="A short summary, for example: International Business student seeking a graduation internship.",
    )
    long_description = models.TextField(
        blank=True,
        help_text="Describe your background, interests, goals, constraints, and anything the assistant should understand.",
    )
    linkedin_url = models.URLField(max_length=500, blank=True)
    linkedin_source_text = models.TextField(
        blank=True,
        help_text="Text copied from LinkedIn. Kept as private evidence for profile comparison.",
    )
    profile_draft = models.TextField(
        blank=True,
        help_text="A live profile draft assembled from the interview. You can edit it freely.",
    )
    document_analysis_status = models.CharField(
        max_length=20,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.NOT_STARTED,
    )
    document_profile_proposal = models.TextField(blank=True)
    document_structured_proposal = models.JSONField(default=dict, blank=True)
    structured_profile = models.JSONField(default=dict, blank=True)
    document_evidence = models.JSONField(default=list, blank=True)
    document_questions = models.JSONField(default=list, blank=True)
    document_analysis_error = models.TextField(blank=True)
    document_analyzed_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or "My profile"


class ProfileInterviewAnswer(models.Model):
    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="interview_answers")
    question_key = models.CharField(max_length=80)
    question = models.TextField()
    section_title = models.CharField(max_length=120)
    answer = models.TextField()
    position = models.PositiveSmallIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["profile", "question_key"], name="unique_profile_question")
        ]

    def __str__(self):
        return self.section_title


class CampaignAttachment(models.Model):
    campaign = models.ForeignKey(SearchCampaign, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="campaign_requests/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name


class ProfileDocument(models.Model):
    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="documents")
    label = models.CharField(max_length=160)
    file = models.FileField(upload_to="profile_documents/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.label


class Organization(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Opportunity(models.Model):
    class Kind(models.TextChoices):
        ADVERTISED = "advertised", "Advertised role"
        COLD_OUTREACH = "cold_outreach", "Cold-outreach target"

    class Status(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        QUALIFIED = "qualified", "Qualified"
        DRAFT_READY = "draft_ready", "Draft ready"
        APPLIED = "applied", "Applied"
        INTERVIEW = "interview", "Interview"
        REJECTED = "rejected", "Rejected"
        OFFER = "offer", "Offer"

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Research needed"
        QUALIFIED = "qualified", "Qualified"
        CLARIFY = "clarify", "Needs clarification"
        UNSUITABLE = "unsuitable", "Unsuitable"
        UNVERIFIED = "unverified", "Could not verify"

    campaign = models.ForeignKey(SearchCampaign, on_delete=models.CASCADE, related_name="opportunities")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="opportunities")
    title = models.CharField(max_length=240)
    kind = models.CharField(max_length=24, choices=Kind.choices, default=Kind.ADVERTISED)
    location = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(blank=True)
    job_description = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DISCOVERED, db_index=True)
    match_score = models.PositiveSmallIntegerField(blank=True, null=True)
    next_action = models.CharField(max_length=240, blank=True)
    deadline = models.DateField(blank=True, null=True)
    submitted_on = models.DateField(blank=True, null=True)
    fit_summary = models.TextField(blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )
    company_description = models.TextField(blank=True)
    company_location = models.CharField(max_length=200, blank=True)
    company_size = models.CharField(max_length=120, blank=True)
    internship_dates = models.CharField(max_length=200, blank=True)
    work_arrangement = models.CharField(max_length=160, blank=True)
    japanese_requirement = models.CharField(max_length=240, blank=True)
    visa_support = models.CharField(max_length=240, blank=True)
    thesis_compatibility = models.CharField(max_length=240, blank=True)
    requirements_assessment = models.JSONField(default=list, blank=True)
    research_sources = models.JSONField(default=list, blank=True)
    research_summary = models.TextField(blank=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.organization.name} — {self.title}"


class InboxItem(models.Model):
    class RequestType(models.TextChoices):
        JOB = "job", "Job or internship"
        COMPANY = "company", "Company to research"
        UNKNOWN = "unknown", "Let the assistant decide"

    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting for AI analysis"
        PROCESSED = "processed", "Added to applications"
        NEEDS_INPUT = "needs_input", "Needs more information"

    campaign = models.ForeignKey(SearchCampaign, on_delete=models.CASCADE, related_name="inbox_items")
    request_type = models.CharField(max_length=16, choices=RequestType.choices, default=RequestType.UNKNOWN)
    content = models.TextField(blank=True)
    source_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WAITING, db_index=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.SET_NULL, blank=True, null=True, related_name="inbox_sources")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Inbox item {self.pk or 'new'}"


class InboxAttachment(models.Model):
    item = models.ForeignKey(InboxItem, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="job_inbox/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name


class ChatMessage(models.Model):
    """A local record of conversations with Robert."""

    class Scope(models.TextChoices):
        GENERAL = "general", "Robert"
        PROFILE = "profile", "Profile interview"
        CAMPAIGN = "campaign", "Campaign setup"

    class Role(models.TextChoices):
        USER = "user", "You"
        ASSISTANT = "assistant", "Robert"

    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.GENERAL, db_index=True)
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    campaign = models.ForeignKey(
        SearchCampaign,
        on_delete=models.CASCADE,
        related_name="chat_messages",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class AIUsage(models.Model):
    purpose = models.CharField(max_length=32)
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
