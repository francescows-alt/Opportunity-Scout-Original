from django.urls import path

from . import views


urlpatterns = [
    path("", views.campaign_list, name="campaign-list"),
    path("campaigns/new/", views.campaign_create, name="campaign-create"),
    path("campaigns/<int:campaign_id>/edit/", views.campaign_edit, name="campaign-edit"),
]
