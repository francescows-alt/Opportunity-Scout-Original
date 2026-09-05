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


class SearchCycle(models.Model):
    """A permanent memory of how one autonomous search was performed."""

    campaign = models.ForeignKey(SearchCampaign, on_delete=models.CASCADE, related_name="search_cycles")
    sequence = models.PositiveIntegerField()
    strategy = models.CharField(max_length=240)
    queries = models.JSONField(default=list, blank=True)
    sources = models.JSONField(default=list, blank=True)
    found_count = models.PositiveSmallIntegerField(default=0)
    added_count = models.PositiveSmallIntegerField(default=0)
    duplicate_count = models.PositiveSmallIntegerField(default=0)
    fee_blocked_count = models.PositiveSmallIntegerField(default=0)
    raw_results = models.JSONField(
        default=list,
        blank=True,
        help_text="Everything the search returned, before the app filtered anything out.",
    )
    rejections = models.JSONField(
        default=list,
        blank=True,
        help_text="Results the app dropped, each with the reason, so over-filtering stays visible.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sequence"]
        constraints = [
            models.UniqueConstraint(fields=["campaign", "sequence"], name="unique_campaign_search_cycle"),
        ]


class SearchJob(models.Model):
    """Progress ticket for one end-to-end local search and research run."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    class Kind(models.TextChoices):
        SEARCH = "search", "Full search"
        RESEARCH = "research", "Deep research"
        LINK_CHECK = "link_check", "Link check"

    campaign = models.ForeignKey(SearchCampaign, on_delete=models.CASCADE, related_name="search_jobs")
    kind = models.CharField(
        max_length=16, choices=Kind.choices, default=Kind.SEARCH, db_index=True,
        help_text="Different kinds run independently: a link check must never block a search.",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    stage = models.CharField(max_length=32, default="queued")
    progress = models.PositiveSmallIntegerField(default=3)
    message = models.CharField(max_length=300, default="Preparing Robert’s search…")
    found_count = models.PositiveSmallIntegerField(default=0)
    added_count = models.PositiveSmallIntegerField(default=0)
    researched_count = models.PositiveSmallIntegerField(default=0)
    duplicate_count = models.PositiveSmallIntegerField(default=0)
    fee_blocked_count = models.PositiveSmallIntegerField(default=0)
    opportunity_ids = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


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
    logo_url = models.URLField(max_length=500, blank=True)
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
        EXPIRED = "expired", "Expired"
        UNVERIFIED = "unverified", "Could not verify"

    class QualityFlag(models.TextChoices):
        GOOD = "good", "Good result"
        BAD = "bad", "Bad result"

    class DeletedBy(models.TextChoices):
        YOU = "you", "You"
        ROBERT = "robert", "Robert"

    class LinkCheck(models.TextChoices):
        CONFIRMED = "confirmed", "Vacancy found on the page"
        NOT_FOUND = "not_found", "Vacancy not on the page"
        LANDING_PAGE = "landing_page", "Careers page, not this vacancy"
        UNCHECKED = "unchecked", "Could not check"

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
    next_action_is_manual = models.BooleanField(
        default=False,
        help_text="Set when you write your own next action, so repeated research cannot overwrite it.",
    )
    is_favorite = models.BooleanField(default=False, db_index=True)
    search_cycle = models.ForeignKey(
        SearchCycle,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="found_opportunities",
        help_text="The search that produced this row, so a bad result traces back to its queries.",
    )
    quality_flag = models.CharField(
        max_length=8,
        choices=QualityFlag.choices,
        blank=True,
        db_index=True,
        help_text="Your verdict on this result. Blank until you say so; never inferred.",
    )
    quality_note = models.TextField(
        blank=True,
        help_text="Why this result was good or bad, in your own words.",
    )
    deleted_at = models.DateTimeField(
        blank=True, null=True, db_index=True,
        help_text="Set when this moves to the Deleted folder. The row is never removed from the database.",
    )
    deleted_reason = models.TextField(blank=True, help_text="Why it was deleted, in plain words.")
    deleted_by = models.CharField(max_length=8, choices=DeletedBy.choices, blank=True)
    link_check_status = models.CharField(
        max_length=16, choices=LinkCheck.choices, blank=True, db_index=True,
        help_text="What a real browser saw at the application link. Blank until checked.",
    )
    link_check_note = models.TextField(blank=True, help_text="What the page actually said, so you can judge it yourself.")
    link_checked_at = models.DateTimeField(blank=True, null=True)
    canonical_url = models.URLField(max_length=500, blank=True, db_index=True)
    fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
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
    company_country = models.CharField(max_length=120, blank=True)
    company_industry = models.CharField(max_length=160, blank=True)
    company_reputation = models.TextField(blank=True)
    cv_value = models.TextField(blank=True)
    international_environment = models.TextField(blank=True)
    growth_outlook = models.TextField(blank=True)
    work_culture = models.TextField(blank=True)
    internship_dates = models.CharField(max_length=200, blank=True)
    internship_start_date = models.DateField(blank=True, null=True)
    internship_end_date = models.DateField(blank=True, null=True)
    minimum_duration = models.CharField(max_length=160, blank=True)
    application_deadline_text = models.CharField(max_length=200, blank=True)
    responsibilities = models.JSONField(default=list, blank=True)
    what_you_would_do = models.TextField(blank=True)
    what_company_needs = models.TextField(blank=True)
    candidate_fee_required = models.BooleanField(default=False)
    candidate_fee = models.CharField(max_length=200, blank=True)
    compensation = models.CharField(max_length=200, blank=True)
    work_arrangement = models.CharField(max_length=160, blank=True)
    japanese_requirement = models.CharField(max_length=240, blank=True)
    posting_language = models.CharField(max_length=40, blank=True)
    posting_language_note = models.CharField(max_length=300, blank=True)
    japanese_only_inferred = models.BooleanField(default=False)
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
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "canonical_url"],
                condition=~models.Q(canonical_url=""),
                name="unique_campaign_canonical_url",
            ),
            models.UniqueConstraint(
                fields=["campaign", "fingerprint"],
                condition=~models.Q(fingerprint=""),
                name="unique_campaign_opportunity_fingerprint",
            ),
        ]

    def __str__(self):
        return f"{self.organization.name} — {self.title}"


class InboxItem(models.Model):
    class RequestType(models.TextChoices):
        JOB = "job", "Job or internship"
        COMPANY = "company", "Company to research"
        UNKNOWN = "unknown", "Let the assistant decide"

    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting for AI analysis"
        ANALYZING = "analyzing", "Robert is researching this"
        PROCESSED = "processed", "Added to applications"
        NEEDS_INPUT = "needs_input", "Needs more information"

    campaign = models.ForeignKey(SearchCampaign, on_delete=models.CASCADE, related_name="inbox_items")
    request_type = models.CharField(max_length=16, choices=RequestType.choices, default=RequestType.UNKNOWN)
    content = models.TextField(blank=True)
    source_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WAITING, db_index=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.SET_NULL, blank=True, null=True, related_name="inbox_sources")
    analysis_note = models.TextField(
        blank=True,
        help_text="What Robert concluded, or the question he needs answered before this can become an application.",
    )
    analyzed_at = models.DateTimeField(blank=True, null=True)
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
