from django import forms
from django.core.validators import FileExtensionValidator

from .models import (
    CampaignAttachment,
    CandidateProfile,
    InboxAttachment,
    InboxItem,
    Opportunity,
    Organization,
    SearchCampaign,
)


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
        fields = ["full_name", "headline", "long_description", "profile_draft"]
        widgets = {
            "long_description": forms.Textarea(attrs={"rows": 8, "data-dictation": "true"}),
            "profile_draft": forms.Textarea(attrs={"rows": 16, "data-dictation": "true"}),
        }
        labels = {
            "long_description": "Anything else the assistant should know",
            "profile_draft": "Live editable profile",
        }


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data and not self.required:
            return []
        clean_one = super().clean
        if isinstance(data, (list, tuple)):
            return [clean_one(item, initial) for item in data]
        return [clean_one(data, initial)]


ALLOWED_DOCUMENT_TYPES = ["pdf", "doc", "docx", "txt", "png", "jpg", "jpeg", "webp"]


class ProfileDocumentUploadForm(forms.Form):
    label = forms.CharField(
        max_length=120,
        required=False,
        help_text="Optional group label, such as CV or University documents.",
    )
    files = MultipleFileField(
        validators=[FileExtensionValidator(ALLOWED_DOCUMENT_TYPES)],
        help_text="Select one or several files.",
    )

    def clean_files(self):
        files = self.cleaned_data["files"]
        if any(uploaded_file.size > 10 * 1024 * 1024 for uploaded_file in files):
            raise forms.ValidationError("Each file must be smaller than 10 MB.")
        if sum(uploaded_file.size for uploaded_file in files) > 30 * 1024 * 1024:
            raise forms.ValidationError("The combined upload must be smaller than 30 MB.")
        return files


class QuickInboxForm(forms.ModelForm):
    files = MultipleFileField(
        required=False,
        validators=[FileExtensionValidator(ALLOWED_DOCUMENT_TYPES)],
        help_text="Screenshots, PDFs, Word documents, or text files.",
    )

    class Meta:
        model = InboxItem
        fields = ["campaign", "request_type", "content", "source_url"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 10,
                "placeholder": "Paste a vacancy, describe a company, or write what you want researched…",
                "data-dictation": "true",
            }),
        }

    def clean_files(self):
        files = self.cleaned_data.get("files", [])
        if any(uploaded_file.size > 10 * 1024 * 1024 for uploaded_file in files):
            raise forms.ValidationError("Each file must be smaller than 10 MB.")
        return files

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("content") and not cleaned_data.get("source_url") and not cleaned_data.get("files"):
            raise forms.ValidationError("Paste text, add a link, or upload at least one file.")
        return cleaned_data

    def save(self, commit=True):
        item = super().save(commit=commit)
        if commit:
            for uploaded_file in self.cleaned_data.get("files", []):
                InboxAttachment.objects.create(item=item, file=uploaded_file)
        return item


class CampaignPromptForm(forms.Form):
    name = forms.CharField(
        max_length=120,
        required=False,
        help_text="Optional. The AI can suggest a name later.",
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 12,
            "placeholder": "Describe the job search you want in ordinary language…",
            "data-dictation": "true",
        })
    )
    files = MultipleFileField(
        required=False,
        validators=[FileExtensionValidator(ALLOWED_DOCUMENT_TYPES)],
        help_text="Optional supporting documents or screenshots.",
    )

    def clean_files(self):
        files = self.cleaned_data.get("files", [])
        if any(uploaded_file.size > 10 * 1024 * 1024 for uploaded_file in files):
            raise forms.ValidationError("Each file must be smaller than 10 MB.")
        return files

    def save(self):
        description = self.cleaned_data["description"].strip()
        campaign = SearchCampaign.objects.create(
            name=self.cleaned_data.get("name", "").strip() or "New search campaign",
            goal="Waiting for AI interpretation",
            natural_language_brief=description,
            setup_status="waiting_ai",
            is_active=False,
        )
        for uploaded_file in self.cleaned_data.get("files", []):
            CampaignAttachment.objects.create(campaign=campaign, file=uploaded_file)
        return campaign


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
