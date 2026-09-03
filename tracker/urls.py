from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("applications/", views.dashboard, name="dashboard"),
    path("inbox/", views.inbox, name="inbox"),
    path("applications/new/", views.opportunity_create, name="opportunity-create"),
    path("applications/<int:opportunity_id>/edit/", views.opportunity_edit, name="opportunity-edit"),
    path("profile/", views.profile, name="profile"),
    path("search-rules/", views.campaign_list, name="campaign-list"),
    path("campaigns/new/", views.campaign_create, name="campaign-create"),
    path("campaigns/<int:campaign_id>/edit/", views.campaign_edit, name="campaign-edit"),
]
