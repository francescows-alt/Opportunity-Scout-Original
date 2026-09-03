from datetime import date
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from .models import CandidateProfile, Opportunity, ProfileDocument, SearchCampaign


class SearchCampaignTests(TestCase):
    def test_campaign_list_page_loads(self):
        response = self.client.get(reverse("campaign-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your search campaigns")

    def test_user_can_create_campaign(self):
        response = self.client.post(reverse("campaign-create"), {
            "name": "Japan graduation internship 2027",
            "goal": "Graduation internship",
            "locations": "Japan, especially Tokyo",
            "start_date": "2027-02-01",
            "end_date": "2027-06-30",
            "desired_work": "Meaningful and varied business work",
            "avoid_work": "Reception and repetitive administration",
            "is_active": "on",
        })
        self.assertRedirects(response, reverse("campaign-list"))
        campaign = SearchCampaign.objects.get()
        self.assertEqual(campaign.name, "Japan graduation internship 2027")
        self.assertEqual(campaign.start_date, date(2027, 2, 1))

    def test_user_can_edit_campaign(self):
        campaign = SearchCampaign.objects.create(name="Original search", goal="Internship")
        response = self.client.post(reverse("campaign-edit", args=[campaign.id]), {
            "name": "Updated search", "goal": "Graduate job", "locations": "Europe",
        })
        self.assertRedirects(response, reverse("campaign-list"))
        campaign.refresh_from_db()
        self.assertEqual(campaign.name, "Updated search")
        self.assertEqual(campaign.goal, "Graduate job")

    def test_end_date_cannot_be_before_start_date(self):
        response = self.client.post(reverse("campaign-create"), {
            "name": "Invalid dates", "goal": "Internship",
            "start_date": "2027-06-01", "end_date": "2027-02-01",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The end date must be after the start date.")
        self.assertFalse(SearchCampaign.objects.exists())


class DashboardTests(TestCase):
    def setUp(self):
        self.campaign = SearchCampaign.objects.create(name="Japan 2027", goal="Internship")

    def test_user_can_add_opportunity(self):
        response = self.client.post(reverse("opportunity-create"), {
            "campaign": self.campaign.id,
            "company_name": "Example Company",
            "title": "Business Intern",
            "kind": Opportunity.Kind.ADVERTISED,
            "status": Opportunity.Status.DISCOVERED,
            "next_action": "Read the description",
        })
        self.assertRedirects(response, reverse("dashboard"))
        opportunity = Opportunity.objects.get()
        self.assertEqual(opportunity.organization.name, "Example Company")

    def test_dashboard_searches_company_name(self):
        self.client.post(reverse("opportunity-create"), {
            "campaign": self.campaign.id,
            "company_name": "Visible Company",
            "title": "Strategy Intern",
            "kind": Opportunity.Kind.ADVERTISED,
            "status": Opportunity.Status.QUALIFIED,
        })
        response = self.client.get(reverse("dashboard"), {"q": "Visible"})
        self.assertContains(response, "Visible Company")
        response = self.client.get(reverse("dashboard"), {"q": "Missing"})
        self.assertNotContains(response, "Visible Company")

    def test_dashboard_paginates_large_lists(self):
        for number in range(26):
            self.client.post(reverse("opportunity-create"), {
                "campaign": self.campaign.id,
                "company_name": f"Company {number}",
                "title": "Intern",
                "kind": Opportunity.Kind.ADVERTISED,
                "status": Opportunity.Status.DISCOVERED,
            })
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(len(response.context["page"].object_list), 25)
        self.assertEqual(response.context["page"].paginator.num_pages, 2)


class CandidateProfileTests(TestCase):
    def test_user_can_save_long_description(self):
        response = self.client.post(reverse("profile"), {
            "action": "save_profile",
            "full_name": "Francesco",
            "headline": "International Business student",
            "long_description": "A long and truthful description of my background.",
        })
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(CandidateProfile.objects.get(pk=1).full_name, "Francesco")

    def test_user_can_upload_profile_document(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            uploaded_file = SimpleUploadedFile("cv.pdf", b"example CV", content_type="application/pdf")
            response = self.client.post(reverse("profile"), {
                "action": "upload_document",
                "label": "Current CV",
                "file": uploaded_file,
            })
            self.assertRedirects(response, reverse("profile"))
            self.assertEqual(ProfileDocument.objects.get().label, "Current CV")
