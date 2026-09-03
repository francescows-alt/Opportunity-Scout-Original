from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("applications/", views.dashboard, name="dashboard"),
    path("applications/discover/", views.discover_internships, name="discover-internships"),
    path("applications/qualify/", views.qualify_discoveries, name="qualify-discoveries"),
    path("inbox/", views.inbox, name="inbox"),
    path("applications/new/", views.opportunity_create, name="opportunity-create"),
    path("applications/<int:opportunity_id>/edit/", views.opportunity_edit, name="opportunity-edit"),
    path("applications/<int:opportunity_id>/favorite/", views.toggle_favorite, name="opportunity-favorite"),
    path("profile/", views.profile, name="profile"),
    path("search-rules/", views.campaign_list, name="campaign-list"),
    path("campaigns/new/", views.campaign_create, name="campaign-create"),
    path("campaigns/<int:campaign_id>/setup/", views.campaign_setup, name="campaign-setup"),
    path("campaigns/new/advanced/", views.campaign_create_advanced, name="campaign-create-advanced"),
    path("campaigns/<int:campaign_id>/edit/", views.campaign_edit, name="campaign-edit"),
    path("robert/send/", views.robert_send, name="robert-send"),
    path("api/transcribe/", views.transcribe_audio, name="transcribe-audio"),
]
