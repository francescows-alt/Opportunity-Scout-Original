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
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or "My profile"


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
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.organization.name} — {self.title}"
