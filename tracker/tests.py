from datetime import date

from django.test import TestCase
from django.urls import reverse

from .models import SearchCampaign


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
