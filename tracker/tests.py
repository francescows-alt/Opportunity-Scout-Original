from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from .ai import DocumentProfileAnalysis, EvidenceItem, InternshipDiscoveryBatch, OpportunityResearchBatch
from .models import CandidateProfile, ChatMessage, InboxAttachment, InboxItem, Opportunity, Organization, ProfileDocument, SearchCampaign, SearchCycle, SearchJob


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

    def test_dashboard_leads_with_autonomous_discovery(self):
        CandidateProfile.objects.create(pk=1, profile_draft="Business student")
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Let Robert search first")
        self.assertContains(response, "Find &amp; research internships")

    @patch("tracker.views.research_internships")
    def test_robert_discovery_adds_source_backed_opportunity(self, research):
        CandidateProfile.objects.create(pk=1, profile_draft="Business student")
        research.return_value = InternshipDiscoveryBatch(
            summary="One relevant role found.",
            search_strategy="Direct employer pages",
            queries_used=["Tokyo growth internship 2027"],
            sources_searched=["Employer careers"],
            opportunities=[{
                "company": "Example Japan", "title": "Growth Intern",
                "kind": "advertised", "location": "Tokyo, Japan",
                "source_url": "https://example.com/jobs/growth-intern",
                "description": "A real example vacancy.", "match_score": 82,
                "fit_summary": "Relevant international growth work.",
                "missing_information": ["Visa support"],
                "candidate_fee_required": False, "candidate_fee": "None found",
                "compensation": "Not stated",
                "next_action": "Verify visa support and internship dates.",
            }],
        )
        response = self.client.post(reverse("discover-internships"))
        self.assertRedirects(response, reverse("dashboard"))
        opportunity = Opportunity.objects.get()
        self.assertEqual(opportunity.organization.name, "Example Japan")
        self.assertEqual(opportunity.match_score, 82)
        self.assertIn("Unknown: Visa support", opportunity.fit_summary)
        self.assertEqual(opportunity.status, Opportunity.Status.DISCOVERED)
        self.assertEqual(SearchCycle.objects.get().added_count, 1)

    def test_user_can_favorite_an_opportunity(self):
        organization = Organization.objects.create(name="Favorite Company")
        opportunity = Opportunity.objects.create(
            campaign=self.campaign, organization=organization, title="Strategy Intern",
        )
        response = self.client.post(reverse("opportunity-favorite", args=[opportunity.id]))
        self.assertRedirects(response, f"{reverse('dashboard')}?selected={opportunity.id}")
        opportunity.refresh_from_db()
        self.assertTrue(opportunity.is_favorite)
        favorites = self.client.get(reverse("dashboard"), {"review": "favorites"})
        self.assertContains(favorites, "Favorite Company")

    @patch("tracker.views.Thread")
    def test_one_click_search_creates_background_progress_ticket(self, thread):
        CandidateProfile.objects.create(pk=1, profile_draft="Business student")
        response = self.client.post(reverse("search-start"))
        self.assertEqual(response.status_code, 202)
        job = SearchJob.objects.get()
        self.assertEqual(response.json()["job_id"], job.id)
        thread.assert_called_once()
        status = self.client.get(reverse("search-job-status", args=[job.id])).json()
        self.assertEqual(status["stage"], "queued")

    @patch("django.test.Client")
    def test_background_search_reaches_complete_stage(self, client_class):
        from .views import _run_complete_search

        job = SearchJob.objects.create(campaign=self.campaign)

        def simulate_stage(url, data=None):
            if url == reverse("discover-internships"):
                SearchCycle.objects.create(
                    campaign=self.campaign, sequence=1, strategy="Employer pages",
                    found_count=0, added_count=0,
                )
            return self.client.get(reverse("dashboard"))

        client_class.return_value.post.side_effect = simulate_stage
        _run_complete_search(job.id)
        job.refresh_from_db()
        self.assertEqual(job.status, SearchJob.Status.COMPLETE)
        self.assertEqual(job.progress, 100)

    def test_research_only_start_requires_pending_items(self):
        CandidateProfile.objects.create(pk=1, profile_draft="Business student")
        response = self.client.post(reverse("research-start"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("no discoveries waiting", response.json()["error"])

    @patch("django.test.Client")
    def test_research_only_loops_through_all_pending_batches(self, client_class):
        from .views import _run_research_only

        organization = Organization.objects.create(name="Needs Research Co")
        for number in range(10):
            Opportunity.objects.create(campaign=self.campaign, organization=organization, title=f"Intern {number}")
        job = SearchJob.objects.create(campaign=self.campaign)

        def simulate_research(url, data=None):
            chunk_ids = [int(value) for value in data["opportunity_ids"]]
            Opportunity.objects.filter(pk__in=chunk_ids).update(verified_at=timezone.now())
            return self.client.get(reverse("dashboard"))

        client_class.return_value.post.side_effect = simulate_research
        _run_research_only(job.id)
        job.refresh_from_db()
        self.assertEqual(job.status, SearchJob.Status.COMPLETE)
        self.assertEqual(job.progress, 100)
        self.assertEqual(client_class.return_value.post.call_count, 2)
        self.assertEqual(Opportunity.objects.filter(verified_at__isnull=False).count(), 10)
        self.assertNotIn("still needing retry", job.message)

    def test_selected_role_shows_priority_banner_and_score_tone(self):
        organization = Organization.objects.create(name="Excellent Company")
        opportunity = Opportunity.objects.create(
            campaign=self.campaign, organization=organization, title="Growth Intern",
            verification_status=Opportunity.VerificationStatus.QUALIFIED,
            match_score=91, deadline=timezone.localdate() + timedelta(days=30),
        )
        response = self.client.get(reverse("dashboard"), {"selected": opportunity.id})
        self.assertContains(response, "High-priority match")
        self.assertContains(response, "match-excellent")

        opportunity.deadline = timezone.localdate() + timedelta(days=5)
        opportunity.save(update_fields=["deadline", "updated_at"])
        urgent = self.client.get(reverse("dashboard"), {"selected": opportunity.id})
        self.assertContains(urgent, "Deadline in 5 days")

    @patch("tracker.views.research_internships")
    def test_discovery_blocks_duplicate_roles_and_candidate_fees(self, research):
        CandidateProfile.objects.create(pk=1, profile_draft="Business student")
        organization = Organization.objects.create(name="Existing Co")
        existing = Opportunity.objects.create(
            campaign=self.campaign, organization=organization, title="Growth Intern",
            location="Tokyo", source_url="https://existing.example/jobs/123",
            verification_status=Opportunity.VerificationStatus.QUALIFIED,
        )
        common = {
            "kind": "advertised", "location": "Tokyo", "description": "Role details",
            "match_score": 70, "fit_summary": "Possible fit", "missing_information": [],
            "compensation": "Not stated", "next_action": "Review source",
        }
        research.return_value = InternshipDiscoveryBatch(
            summary="Checked duplicate and fee controls.", search_strategy="New keyword method",
            queries_used=["new query"], sources_searched=["Employer pages"],
            opportunities=[
                {**common, "company": "Existing Co", "title": "Growth Intern",
                 "source_url": "https://other-board.example/growth-intern",
                 "candidate_fee_required": False, "candidate_fee": "None found"},
                {**common, "company": "Fee Program", "title": "Tokyo Internship",
                 "source_url": "https://fees.example/tokyo",
                 "candidate_fee_required": True, "candidate_fee": "USD 11,450"},
            ],
        )
        self.client.post(reverse("discover-internships"))
        # The duplicate is skipped entirely, but the fee-charging program is now kept
        # (marked unsuitable) so Robert remembers it and never re-researches it later.
        self.assertEqual(Opportunity.objects.count(), 2)
        existing.refresh_from_db()
        self.assertEqual(existing.verification_status, Opportunity.VerificationStatus.QUALIFIED)
        fee_opportunity = Opportunity.objects.get(title="Tokyo Internship")
        self.assertEqual(fee_opportunity.verification_status, Opportunity.VerificationStatus.UNSUITABLE)
        self.assertTrue(fee_opportunity.candidate_fee_required)
        self.assertIsNotNone(fee_opportunity.verified_at)
        cycle = SearchCycle.objects.get()
        self.assertEqual(cycle.duplicate_count, 1)
        self.assertEqual(cycle.fee_blocked_count, 1)
        self.assertEqual(cycle.added_count, 0)

    @patch("tracker.views.qualify_opportunities")
    def test_robert_qualification_builds_practical_report(self, qualify):
        CandidateProfile.objects.create(pk=1, profile_draft="Business student with marketing experience")
        organization = Organization.objects.create(name="Example Japan")
        opportunity = Opportunity.objects.create(
            campaign=self.campaign, organization=organization, title="Growth Intern",
            source_url="https://example.com/jobs/growth-intern", match_score=70,
        )
        qualify.return_value = OpportunityResearchBatch(
            summary="The role is promising but visa support needs confirmation.",
            reports=[{
                "opportunity_id": opportunity.id, "verdict": "clarify",
                "company_description": "An international technology company serving Japan.",
                "company_location": "Tokyo, Japan", "company_size": "Small company",
                "company_country": "Japan", "company_industry": "B2B software",
                "company_website": "https://example.com/", "internship_location": "Tokyo, Japan",
                "company_logo_url": "https://example.com/logo.png",
                "company_reputation": "Known in its specialist market.",
                "cv_value": "Provides relevant international growth evidence.",
                "international_environment": "International customer base.",
                "growth_outlook": "No reliable growth figures found.",
                "work_culture": "Not established by reliable public sources.",
                "internship_dates": "Feb–Jul 2027",
                "internship_start_date_iso": "2027-02-01",
                "internship_end_date_iso": "2027-07-31",
                "minimum_duration": "6 months", "work_arrangement": "Hybrid",
                "application_deadline": "Not stated in the source",
                "application_deadline_iso": None,
                "japanese_requirement": "Intermediate Japanese preferred",
                "posting_language": "English",
                "posting_language_note": "The full vacancy is written in English; this does not prove Japanese is unnecessary.",
                "japanese_only_inferred": False,
                "visa_support": "Not stated in the source",
                "thesis_compatibility": "Requires confirmation",
                "role_summary": "Supports growth research and campaigns.", "match_score": 84,
                "responsibilities": ["Research customers", "Support campaigns"],
                "what_you_would_do": "Research customer segments and support campaign execution across the week.",
                "what_company_needs": "A student with verified marketing experience and sufficient availability.",
                "candidate_fee_required": False, "candidate_fee": "None found",
                "compensation": "JPY 80,000 monthly",
                "fit_summary": "Strong functional fit with practical questions outstanding.",
                "requirements": [
                    {"requirement": "Marketing experience", "status": "have", "evidence": "Verified Mobal experience."},
                    {"requirement": "Native Japanese", "status": "unclear", "evidence": "The source does not state a native requirement."},
                    {"requirement": "Self-motivated and proactive", "status": "have", "evidence": "Generic personality trait."},
                ],
                "sources": [{"title": "Official role", "url": "https://example.com/jobs/growth-intern"}],
                "next_action": "Ask HR about visa support and thesis supervision.",
            }],
        )
        response = self.client.post(reverse("qualify-discoveries"))
        self.assertRedirects(response, reverse("dashboard"))
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.verification_status, Opportunity.VerificationStatus.CLARIFY)
        self.assertEqual(opportunity.japanese_requirement, "Intermediate Japanese preferred")
        self.assertEqual(opportunity.posting_language, "English")
        self.assertEqual(str(opportunity.internship_start_date), "2027-02-01")
        self.assertEqual(opportunity.minimum_duration, "6 months")
        self.assertEqual(opportunity.application_deadline_text, "Not stated in the source")
        self.assertEqual(opportunity.company_country, "Japan")
        self.assertEqual(opportunity.company_industry, "B2B software")
        self.assertEqual(opportunity.responsibilities[0], "Research customers")
        self.assertIn("customer segments", opportunity.what_you_would_do)
        self.assertEqual(opportunity.compensation, "JPY 80,000 monthly")
        self.assertEqual(opportunity.requirements_assessment[0]["status"], "have")
        self.assertEqual(len(opportunity.requirements_assessment), 2)
        self.assertNotIn("proactive", str(opportunity.requirements_assessment).lower())
        self.assertEqual(opportunity.research_sources[0]["title"], "Official role")
        self.assertIsNotNone(opportunity.verified_at)

        list_only = self.client.get(reverse("dashboard"))
        self.assertNotContains(list_only, "Application page")

        report = self.client.get(reverse("dashboard"), {"selected": opportunity.id})
        self.assertContains(report, "All applications")
        self.assertContains(report, "Application page")
        self.assertContains(report, "Official website")
        self.assertContains(report, "B2B software")
        self.assertContains(report, "Japanese")
        self.assertContains(report, "Posting language")
        self.assertContains(report, "1 Feb 2027")
        self.assertContains(report, "Match")
        self.assertContains(report, "Check")
        self.assertContains(report, "More about Example Japan")
        self.assertContains(report, "Main responsibilities")
        self.assertContains(report, "What you would actually do")
        self.assertContains(report, "What the company needs")
        self.assertNotContains(report, "Robert’s verdict")
        self.assertNotContains(report, "Autonomous discovery")
        self.assertNotContains(report, "Ask Robert")
        self.assertNotContains(report, "Application totals")
        page_html = report.content.decode()
        self.assertLess(page_html.index("back-to-list"), page_html.index("Other opportunities"))

    @patch("tracker.views.qualify_opportunities")
    def test_qualification_rejects_non_image_logo_urls(self, qualify):
        CandidateProfile.objects.create(pk=1, profile_draft="Business student")
        organization = Organization.objects.create(name="Homepage Only Co")
        opportunity = Opportunity.objects.create(
            campaign=self.campaign, organization=organization, title="Growth Intern",
            source_url="https://example.com/jobs/growth-intern", match_score=70,
        )
        qualify.return_value = OpportunityResearchBatch(
            summary="Checked the logo link.",
            reports=[{
                "opportunity_id": opportunity.id, "verdict": "clarify",
                "company_description": "A company.", "company_location": "Tokyo, Japan",
                "company_size": "11–50 employees", "company_country": "Japan",
                "company_industry": "SaaS", "company_website": "https://example.com/",
                "internship_location": "Tokyo, Japan",
                "company_logo_url": "https://example.com/",
                "company_reputation": "Not established by reliable public sources.",
                "cv_value": "Some relevant evidence.", "international_environment": "Not established.",
                "growth_outlook": "Not established.", "work_culture": "Not established.",
                "internship_dates": "Not stated", "internship_start_date_iso": None,
                "internship_end_date_iso": None, "minimum_duration": "Not stated",
                "work_arrangement": "Not stated", "application_deadline": "Not stated",
                "application_deadline_iso": None, "japanese_requirement": "Not stated",
                "posting_language": "English", "posting_language_note": "Written in English.",
                "japanese_only_inferred": False, "visa_support": "Not stated",
                "thesis_compatibility": "Requires confirmation",
                "role_summary": "Supports growth work.", "match_score": 60,
                "responsibilities": ["Support campaigns"],
                "what_you_would_do": "Support marketing campaigns day to day for the team.",
                "what_company_needs": "A student available for the internship period.",
                "candidate_fee_required": False, "candidate_fee": "None found",
                "compensation": "Not stated", "fit_summary": "Reasonable functional fit.",
                "requirements": [], "sources": [], "next_action": "Confirm visa support.",
            }],
        )
        self.client.post(reverse("qualify-discoveries"))
        organization.refresh_from_db()
        self.assertEqual(organization.logo_url, "")

    @patch("tracker.views.qualify_opportunities")
    def test_one_bad_report_does_not_block_the_rest_of_the_batch(self, qualify):
        CandidateProfile.objects.create(pk=1, profile_draft="Business student")
        organization_a = Organization.objects.create(name="Company One")
        organization_b = Organization.objects.create(name="Company Two")
        opportunity_a = Opportunity.objects.create(
            campaign=self.campaign, organization=organization_a, title="Role One",
            source_url="https://example.com/jobs/one",
        )
        opportunity_b = Opportunity.objects.create(
            campaign=self.campaign, organization=organization_b, title="Role Two",
            source_url="https://example.com/jobs/two",
        )

        def make_report(opportunity_id):
            return {
                "opportunity_id": opportunity_id, "verdict": "clarify",
                "company_description": "A company.", "company_location": "Tokyo, Japan",
                "company_size": "11–50 employees", "company_country": "Japan",
                "company_industry": "SaaS", "company_website": "https://example.com/",
                "internship_location": "Tokyo, Japan", "company_logo_url": "",
                "company_reputation": "Not established by reliable public sources.",
                "cv_value": "Some relevant evidence.", "international_environment": "Not established.",
                "growth_outlook": "Not established.", "work_culture": "Not established.",
                "internship_dates": "Not stated", "internship_start_date_iso": None,
                "internship_end_date_iso": None, "minimum_duration": "Not stated",
                "work_arrangement": "Not stated", "application_deadline": "Not stated",
                "application_deadline_iso": None, "japanese_requirement": "Not stated",
                "posting_language": "English", "posting_language_note": "Written in English.",
                "japanese_only_inferred": False, "visa_support": "Not stated",
                "thesis_compatibility": "Requires confirmation",
                "role_summary": "Supports growth work.", "match_score": 60,
                "responsibilities": ["Support campaigns"],
                "what_you_would_do": "Support marketing campaigns day to day for the team.",
                "what_company_needs": "A student available for the internship period.",
                "candidate_fee_required": False, "candidate_fee": "None found",
                "compensation": "Not stated", "fit_summary": "Reasonable functional fit.",
                "requirements": [], "sources": [], "next_action": "Confirm visa support.",
            }

        qualify.return_value = OpportunityResearchBatch(
            summary="Checked both roles.",
            reports=[make_report(opportunity_a.id), make_report(opportunity_b.id)],
        )

        real_save = Opportunity.save

        def flaky_save(self, *args, **kwargs):
            if self.pk == opportunity_a.id:
                raise RuntimeError("simulated save failure")
            return real_save(self, *args, **kwargs)

        with patch.object(Opportunity, "save", flaky_save):
            self.client.post(reverse("qualify-discoveries"))

        opportunity_a.refresh_from_db()
        opportunity_b.refresh_from_db()
        self.assertIsNone(opportunity_a.verified_at)
        self.assertIsNotNone(opportunity_b.verified_at)
        self.assertEqual(opportunity_b.verification_status, Opportunity.VerificationStatus.CLARIFY)

    def test_list_shows_company_research_and_expired_label(self):
        organization = Organization.objects.create(
            name="Archived Fintech", logo_url="https://example.com/logo.png",
        )
        Opportunity.objects.create(
            campaign=self.campaign, organization=organization, title="Strategy Intern",
            company_industry="Fintech", company_size="51–200 employees",
            posting_language="Japanese",
            japanese_requirement="Japanese-only (inferred)",
            japanese_only_inferred=True,
            verification_status=Opportunity.VerificationStatus.EXPIRED,
        )
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Industry")
        self.assertContains(response, "51–200 employees")
        self.assertContains(response, "https://example.com/logo.png")
        self.assertContains(response, "Expired")
        self.assertContains(response, "日本語 only")

    def test_serious_list_only_shows_qualified_research(self):
        organization = Organization.objects.create(name="Serious Company")
        Opportunity.objects.create(
            campaign=self.campaign, organization=organization, title="Qualified Internship",
            verification_status=Opportunity.VerificationStatus.QUALIFIED,
        )
        other = Organization.objects.create(name="Still Unchecked")
        Opportunity.objects.create(campaign=self.campaign, organization=other, title="Unknown Internship")
        response = self.client.get(reverse("dashboard"), {"review": "serious"})
        self.assertContains(response, "Serious Company")
        self.assertNotContains(response, "Still Unchecked")


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
