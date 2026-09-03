from django import forms
from django.core.validators import FileExtensionValidator

from .models import CandidateProfile, Opportunity, Organization, ProfileDocument, SearchCampaign


class SearchCampaignForm(forms.ModelForm):
    class Meta:
        model = SearchCampaign
        fields = [
            "name", "goal", "locations", "start_date", "end_date",
            "desired_work", "avoid_work", "work_style", "company_preferences",
            "language_requirements", "visa_requirements",
            "university_requirements", "notes", "is_active",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "desired_work": forms.Textarea(attrs={"rows": 4}),
            "avoid_work": forms.Textarea(attrs={"rows": 4}),
            "work_style": forms.Textarea(attrs={"rows": 3}),
            "company_preferences": forms.Textarea(attrs={"rows": 4}),
            "language_requirements": forms.Textarea(attrs={"rows": 3}),
            "visa_requirements": forms.Textarea(attrs={"rows": 3}),
            "university_requirements": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "The end date must be after the start date.")
        return cleaned_data


class CandidateProfileForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = ["full_name", "headline", "long_description"]
        widgets = {"long_description": forms.Textarea(attrs={"rows": 16})}


class ProfileDocumentForm(forms.ModelForm):
    file = forms.FileField(
        validators=[FileExtensionValidator(["pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"])]
    )

    class Meta:
        model = ProfileDocument
        fields = ["label", "file"]

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if uploaded_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Please upload a file smaller than 10 MB.")
        return uploaded_file


class OpportunityForm(forms.ModelForm):
    company_name = forms.CharField(max_length=200)
    company_website = forms.URLField(required=False)

    class Meta:
        model = Opportunity
        fields = [
            "campaign", "title", "kind", "location", "source_url", "status",
            "match_score", "next_action", "deadline", "submitted_on",
            "job_description", "fit_summary", "notes",
        ]
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "submitted_on": forms.DateInput(attrs={"type": "date"}),
            "job_description": forms.Textarea(attrs={"rows": 8}),
            "fit_summary": forms.Textarea(attrs={"rows": 5}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(["campaign", "company_name", "company_website", "title", "kind", "location", "source_url", "status", "match_score", "next_action", "deadline", "submitted_on", "job_description", "fit_summary", "notes"])
        if self.instance.pk:
            self.fields["company_name"].initial = self.instance.organization.name
            self.fields["company_website"].initial = self.instance.organization.website

    def clean_match_score(self):
        score = self.cleaned_data.get("match_score")
        if score is not None and not 0 <= score <= 100:
            raise forms.ValidationError("Match score must be between 0 and 100.")
        return score

    def save(self, commit=True):
        opportunity = super().save(commit=False)
        company_name = self.cleaned_data["company_name"].strip()
        organization = Organization.objects.filter(name__iexact=company_name).first()
        if organization is None:
            organization = Organization(name=company_name)
        website = self.cleaned_data.get("company_website", "")
        if website:
            organization.website = website
        if commit:
            organization.save()
            opportunity.organization = organization
            opportunity.save()
            self.save_m2m()
        return opportunity
