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
