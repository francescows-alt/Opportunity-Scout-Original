from django.conf import settings

from .ai import is_configured
from .models import ChatMessage


def robert_context(request):
    return {
        "robert_messages": ChatMessage.objects.filter(scope=ChatMessage.Scope.GENERAL).order_by("-created_at")[:6][::-1],
        "robert_is_configured": is_configured(),
        "ai_monthly_budget": settings.AI_MONTHLY_BUDGET_USD,
    }
