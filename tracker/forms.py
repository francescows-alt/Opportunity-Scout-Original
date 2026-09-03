from django import forms

from .models import SearchCampaign


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
