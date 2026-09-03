from django.contrib import admin

from .models import SearchCampaign


@admin.register(SearchCampaign)
class SearchCampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "goal", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "goal", "locations")
