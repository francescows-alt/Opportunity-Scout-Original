from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("applications/", views.dashboard, name="dashboard"),
    path("applications/discover/", views.discover_internships, name="discover-internships"),
    path("applications/search/start/", views.start_complete_search, name="search-start"),
    path("applications/research/start/", views.start_research_only, name="research-start"),
    path("applications/search/<int:job_id>/status/", views.search_job_status, name="search-job-status"),
    path("applications/search/<int:job_id>/stop/", views.stop_search_job, name="search-job-stop"),
    path("applications/qualify/", views.qualify_discoveries, name="qualify-discoveries"),
    path("inbox/", views.inbox, name="inbox"),
    path("inbox/<int:item_id>/analyze/", views.inbox_analyze, name="inbox-analyze"),
    path("applications/new/", views.opportunity_create, name="opportunity-create"),
    path("applications/<int:opportunity_id>/edit/", views.opportunity_edit, name="opportunity-edit"),
    path("applications/<int:opportunity_id>/favorite/", views.toggle_favorite, name="opportunity-favorite"),
    path("applications/<int:opportunity_id>/quality/", views.flag_quality, name="opportunity-quality"),
    path("applications/<int:opportunity_id>/check-link/", views.check_link, name="opportunity-check-link"),
    path("applications/<int:opportunity_id>/verify/", views.verify_vacancy, name="opportunity-verify"),
    path("applications/<int:opportunity_id>/delete/", views.delete_opportunity, name="opportunity-delete"),
    path("applications/<int:opportunity_id>/restore/", views.restore_opportunity, name="opportunity-restore"),
    path("applications/links/check/", views.start_link_check, name="link-check-start"),
    path("profile/", views.profile, name="profile"),
    path("search-rules/", views.campaign_list, name="campaign-list"),
    path("campaigns/new/", views.campaign_create, name="campaign-create"),
    path("campaigns/<int:campaign_id>/setup/", views.campaign_setup, name="campaign-setup"),
    path("campaigns/new/advanced/", views.campaign_create_advanced, name="campaign-create-advanced"),
    path("campaigns/<int:campaign_id>/edit/", views.campaign_edit, name="campaign-edit"),
    path("campaigns/<int:campaign_id>/activate/", views.campaign_activate, name="campaign-activate"),
    path("robert/send/", views.robert_send, name="robert-send"),
    path("api/transcribe/", views.transcribe_audio, name="transcribe-audio"),
]
