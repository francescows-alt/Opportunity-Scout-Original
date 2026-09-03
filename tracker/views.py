from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SearchCampaignForm
from .models import SearchCampaign


def campaign_list(request):
    return render(request, "tracker/campaign_list.html", {"campaigns": SearchCampaign.objects.all()})


def campaign_create(request):
    form = SearchCampaignForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        campaign = form.save()
        messages.success(request, f'Campaign "{campaign.name}" was created.')
        return redirect("campaign-list")
    return render(request, "tracker/campaign_form.html", {
        "form": form, "page_title": "Create a search campaign",
    })


def campaign_edit(request, campaign_id):
    campaign = get_object_or_404(SearchCampaign, id=campaign_id)
    form = SearchCampaignForm(request.POST or None, instance=campaign)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'Campaign "{campaign.name}" was updated.')
        return redirect("campaign-list")
    return render(request, "tracker/campaign_form.html", {
        "form": form, "page_title": "Edit search campaign", "campaign": campaign,
    })
