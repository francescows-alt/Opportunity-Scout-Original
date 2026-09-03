from django.contrib import admin

from .models import (
    CandidateProfile,
    CampaignAttachment,
    InboxAttachment,
    InboxItem,
    Opportunity,
    Organization,
    ProfileDocument,
    ProfileInterviewAnswer,
    SearchCampaign,
)


@admin.register(SearchCampaign)
class SearchCampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "goal", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "goal", "locations")


admin.site.register(CandidateProfile)
admin.site.register(ProfileDocument)
admin.site.register(Organization)
admin.site.register(Opportunity)
admin.site.register(InboxItem)
admin.site.register(InboxAttachment)
admin.site.register(ProfileInterviewAnswer)
admin.site.register(CampaignAttachment)
