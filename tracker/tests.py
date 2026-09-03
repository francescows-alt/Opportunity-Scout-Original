from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from .ai import DocumentProfileAnalysis, EvidenceItem
from .models import CandidateProfile, ChatMessage, InboxAttachment, InboxItem, Opportunity, ProfileDocument, SearchCampaign


@override_settings(OPENAI_API_KEY="")
class SearchCampaignTests(TestCase):
    def test_campaign_list_page_loads(self):
        response = self.client.get(reverse("campaign-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your search campaigns")

    def test_user_can_create_campaign_from_plain_language(self):
        response = self.client.post(reverse("campaign-create"), {
            "name": "Japan graduation internship 2027",
            "description": "Find a February to June thesis internship in Japan with visa support.",
        })
        campaign = SearchCampaign.objects.get()
        self.assertRedirects(response, reverse("campaign-setup", args=[campaign.id]))
        self.assertEqual(campaign.name, "Japan graduation internship 2027")
        self.assertEqual(campaign.setup_status, "waiting_ai")
        self.assertIn("visa support", campaign.natural_language_brief)

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
        response = self.client.post(reverse("campaign-create-advanced"), {
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


@override_settings(OPENAI_API_KEY="")
class CandidateProfileTests(TestCase):
    def test_home_starts_at_applications(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_user_can_save_long_description(self):
        response = self.client.post(reverse("profile"), {
            "action": "save_profile",
            "full_name": "Francesco",
            "headline": "International Business student",
            "long_description": "A long and truthful description of my background.",
        })
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(
            CandidateProfile.objects.get(pk=1).long_description,
            "A long and truthful description of my background.",
        )

    def test_user_can_save_linkedin_source(self):
        response = self.client.post(reverse("profile"), {
            "action": "save_linkedin",
            "linkedin_url": "https://www.linkedin.com/in/example-person/",
            "linkedin_source_text": "Experience: Example Company, Growth Intern, 2025.",
        })
        self.assertRedirects(response, reverse("profile"))
        profile = CandidateProfile.objects.get(pk=1)
        self.assertEqual(profile.linkedin_url, "https://www.linkedin.com/in/example-person/")
        self.assertIn("Growth Intern", profile.linkedin_source_text)

    def test_private_background_is_hidden_in_dialog(self):
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "Private background")
        self.assertContains(response, "LinkedIn &amp; documents")
        self.assertContains(response, "Full background essay")
        self.assertContains(response, "background-notes-dialog")

    @patch("tracker.views.analyze_profile_documents")
    def test_linkedin_text_can_be_analyzed_without_documents(self, analyze):
        analyze.return_value = DocumentProfileAnalysis(
            profile={
                "name": "Francesco", "headline": "Business student", "summary": "Truthful summary",
                "experience": [], "education": [], "skill_groups": [], "languages": [],
                "looking_for": [], "not_looking_for": [], "practical_constraints": [],
            },
            evidence=[], important_question=None, summary="Compared the sources.",
        )
        profile = CandidateProfile.objects.create(
            pk=1,
            linkedin_source_text="Example Company — Growth Intern — 2025",
        )
        response = self.client.post(reverse("profile"), {"action": "analyze_documents"})
        self.assertRedirects(response, reverse("profile"))
        profile.refresh_from_db()
        self.assertEqual(profile.document_analysis_status, CandidateProfile.AnalysisStatus.READY)
        self.assertEqual(analyze.call_args.args[2], "Example Company — Growth Intern — 2025")

    def test_user_can_upload_profile_document(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            uploaded_file = SimpleUploadedFile("cv.pdf", b"example CV", content_type="application/pdf")
            response = self.client.post(reverse("profile"), {
                "action": "upload_document",
                "label": "Current CV",
                "files": uploaded_file,
            })
            self.assertRedirects(response, reverse("profile"))
            self.assertTrue(ProfileDocument.objects.get().label.startswith("Current CV"))

    def test_interview_answer_updates_live_profile(self):
        self.client.get(reverse("profile"))
        response = self.client.post(reverse("profile"), {
            "action": "interview_answer",
            "question_key": "education",
            "answer": "I study International Business at Rotterdam Business School.",
        })
        self.assertRedirects(response, reverse("profile"))
        profile = CandidateProfile.objects.get(pk=1)
        self.assertIn("International Business", profile.profile_draft)
        self.assertIn("International Business", profile.long_description)
        self.assertEqual(ChatMessage.objects.filter(scope=ChatMessage.Scope.PROFILE).count(), 3)

    def test_profile_starts_with_robert_question(self):
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "What are you studying")
        self.assertEqual(ChatMessage.objects.filter(scope=ChatMessage.Scope.PROFILE).count(), 1)

    @patch("tracker.views.analyze_profile_documents")
    def test_document_analysis_requires_review_before_updating_profile(self, analyze):
        analyze.return_value = DocumentProfileAnalysis(
            profile={
                "name": "Francesco",
                "headline": "International Business student",
                "summary": "Verified proposed profile",
                "experience": [{
                    "employer": "Example Company", "role": "Business Intern",
                    "date_range": "2025", "location": "Rotterdam",
                    "highlights": ["Completed a relevant project"],
                }],
                "education": [{
                    "institution": "Rotterdam Business School", "qualification": "International Business",
                    "date_range": "2023–2027", "location": "Rotterdam",
                    "highlights": ["Asia track"],
                }],
                "skill_groups": [{"category": "Business", "skills": ["Research"]}],
                "languages": [{"language": "English", "level": "Working proficiency"}],
                "looking_for": ["Meaningful international business work"],
                "not_looking_for": ["Purely administrative work"],
                "practical_constraints": ["Graduation internship"],
            },
            evidence=[EvidenceItem(claim="Studies business", source="cv.pdf", evidence="Business student")],
            important_question="When do you graduate?",
            summary="I extracted the supported facts.",
        )
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.client.post(reverse("profile"), {
                "action": "upload_document",
                "files": SimpleUploadedFile("cv.pdf", b"example CV", content_type="application/pdf"),
            })
            profile = CandidateProfile.objects.get(pk=1)
            profile.profile_draft = "My original long essay"
            profile.save(update_fields=["profile_draft", "updated_at"])
            response = self.client.post(reverse("profile"), {"action": "analyze_documents"})
            self.assertRedirects(response, reverse("profile"))
            profile = CandidateProfile.objects.get(pk=1)
            self.assertEqual(profile.document_analysis_status, CandidateProfile.AnalysisStatus.READY)
            self.assertEqual(profile.profile_draft, "My original long essay")
            self.assertIn("Example Company — Business Intern", profile.document_profile_proposal)
            self.assertEqual(profile.document_structured_proposal["name"], "Francesco")
            review = self.client.get(reverse("profile"))
            self.assertContains(review, "What Francesco is looking for")
            self.assertContains(review, "Keep Robert accurate")

            response = self.client.post(reverse("profile"), {
                "action": "accept_document_profile",
            })
            self.assertRedirects(response, reverse("profile"))
            profile.refresh_from_db()
            self.assertIn("Verified proposed profile", profile.profile_draft)
            self.assertEqual(profile.structured_profile["headline"], "International Business student")
            self.assertEqual(profile.long_description, "My original long essay")


@override_settings(OPENAI_API_KEY="")
class RobertTests(TestCase):
    def test_question_is_saved_and_missing_setup_is_explained(self):
        response = self.client.post(reverse("robert-send"), {
            "message": "What should I do next?",
            "next": reverse("dashboard"),
        })
        self.assertRedirects(response, reverse("dashboard") + "?robert=open")
        messages = ChatMessage.objects.filter(scope=ChatMessage.Scope.GENERAL)
        self.assertEqual(messages.count(), 2)
        self.assertIn("not connected", messages.last().content)

    def test_transcription_explains_missing_ai_setup(self):
        recording = SimpleUploadedFile("dictation.webm", b"audio", content_type="audio/webm")
        response = self.client.post(reverse("transcribe-audio"), {"audio": recording})
        self.assertEqual(response.status_code, 503)
        self.assertIn("not connected", response.json()["error"])


class InboxTests(TestCase):
    def setUp(self):
        self.campaign = SearchCampaign.objects.create(name="Japan 2027", goal="Internship")

    def test_user_can_save_pasted_opportunity(self):
        response = self.client.post(reverse("inbox"), {
            "campaign": self.campaign.id,
            "request_type": InboxItem.RequestType.JOB,
            "content": "Marketing internship in Tokyo with an international company.",
        })
        self.assertRedirects(response, reverse("inbox"))
        item = InboxItem.objects.get()
        self.assertEqual(item.status, InboxItem.Status.WAITING)

    def test_inbox_requires_text_link_or_file(self):
        response = self.client.post(reverse("inbox"), {
            "campaign": self.campaign.id,
            "request_type": InboxItem.RequestType.UNKNOWN,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paste text, add a link, or upload at least one file.")
        self.assertFalse(InboxItem.objects.exists())

    def test_user_can_upload_opportunity_screenshot(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            screenshot = SimpleUploadedFile("job.png", b"fake screenshot bytes", content_type="image/png")
            response = self.client.post(reverse("inbox"), {
                "campaign": self.campaign.id,
                "request_type": InboxItem.RequestType.JOB,
                "files": screenshot,
            })
            self.assertRedirects(response, reverse("inbox"))
            self.assertEqual(InboxAttachment.objects.count(), 1)
