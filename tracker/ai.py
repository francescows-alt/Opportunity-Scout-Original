from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from openai import OpenAI
from pydantic import BaseModel

from .models import AIUsage, CandidateProfile, ChatMessage, InboxItem, Opportunity, SearchCampaign


class AIUnavailable(Exception):
    """A friendly, expected problem such as missing billing or API setup."""


class ProfileTurn(BaseModel):
    reply: str
    revised_profile: str


class CampaignTurn(BaseModel):
    reply: str
    ready: bool = False
    name: str | None = None
    goal: str | None = None
    locations: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    desired_work: str | None = None
    avoid_work: str | None = None
    work_style: str | None = None
    company_preferences: str | None = None
    language_requirements: str | None = None
    visa_requirements: str | None = None
    university_requirements: str | None = None
    notes: str | None = None


def is_configured():
    return bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-key-goes-here")


def _check_budget():
    month_start = timezone.localdate().replace(day=1)
    spent = AIUsage.objects.filter(created_at__date__gte=month_start).aggregate(
        total=Sum("estimated_cost_usd")
    )["total"] or Decimal("0")
    if spent >= Decimal(str(settings.AI_MONTHLY_BUDGET_USD)):
        raise AIUnavailable(
            f"Robert paused because this app's ${settings.AI_MONTHLY_BUDGET_USD:.2f} monthly safety budget was reached."
        )


def _client():
    if not is_configured():
        raise AIUnavailable("OpenAI is not connected yet. Complete the one-time AI setup first.")
    _check_budget()
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _record_text_usage(response, purpose):
    usage = getattr(response, "usage", None)
    if not usage:
        return
    input_tokens = Decimal(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = Decimal(getattr(usage, "output_tokens", 0) or 0)
    # Prices for the intentionally inexpensive default model, per one million tokens.
    estimated = input_tokens * Decimal("0.20") / 1_000_000
    estimated += output_tokens * Decimal("1.20") / 1_000_000
    AIUsage.objects.create(purpose=purpose, estimated_cost_usd=estimated)


def _compact_app_context():
    profile = CandidateProfile.objects.filter(pk=1).first()
    campaigns = SearchCampaign.objects.all()[:5]
    opportunities = Opportunity.objects.select_related("organization").all()[:20]
    return "\n".join([
        "PROFILE:\n" + ((profile.profile_draft or profile.long_description)[:5000] if profile else "Not completed"),
        "CAMPAIGNS:\n" + "\n".join(
            f"- {item.name}: {item.goal}; {item.locations}; {item.setup_status}" for item in campaigns
        ),
        "APPLICATIONS:\n" + "\n".join(
            f"- {item.organization.name}, {item.title}, {item.get_status_display()}, next: {item.next_action}"
            for item in opportunities
        ),
        f"INBOX: {InboxItem.objects.filter(status=InboxItem.Status.WAITING).count()} items waiting for analysis.",
    ])


ROBERT_RULES = """You are Robert, Francesco's professional hiring and internship consultant inside a private local app.
Be candid, practical, encouraging without flattery, and concise. Use the supplied app data, but clearly distinguish verified facts from assumptions.
Never invent experience, qualifications, company facts, contacts, or job requirements. Never claim an application, email, or message was sent.
Nothing may be submitted or sent without Francesco's explicit approval. When information is missing, ask a focused question.
Do not expose private contact information or suggest invasive data gathering; use legitimate public professional contact routes.
"""


def robert_reply(user_text):
    history = list(ChatMessage.objects.filter(scope=ChatMessage.Scope.GENERAL).order_by("-created_at")[:12])
    history.reverse()
    input_messages = [{"role": item.role, "content": item.content} for item in history]
    input_messages.append({"role": "user", "content": user_text})
    response = _client().responses.create(
        model=settings.OPENAI_CHAT_MODEL,
        instructions=ROBERT_RULES + "\nCurrent app summary:\n" + _compact_app_context(),
        input=input_messages,
        max_output_tokens=500,
        store=False,
    )
    _record_text_usage(response, "robert")
    return response.output_text.strip()


def profile_reply(user_text, current_profile):
    history = list(ChatMessage.objects.filter(scope=ChatMessage.Scope.PROFILE).order_by("-created_at")[:16])
    history.reverse()
    input_messages = [{"role": item.role, "content": item.content} for item in history]
    input_messages.append({"role": "user", "content": user_text})
    response = _client().responses.parse(
        model=settings.OPENAI_CHAT_MODEL,
        instructions=ROBERT_RULES + """
You are conducting a deep but friendly candidate interview. Ask ONE useful follow-up question at a time.
Maintain a truthful, detailed source-of-truth profile. Integrate new facts into revised_profile without embellishing them.
Cover education, experience, projects, achievements with evidence, skills/languages, motivations, constraints, work preferences, and personal story.
The reply should briefly acknowledge what was learned, flag ambiguity if needed, then ask the next question.
""" + f"\nExisting editable profile:\n{current_profile[:8000]}",
        input=input_messages,
        text_format=ProfileTurn,
        max_output_tokens=900,
        store=False,
    )
    _record_text_usage(response, "profile")
    return response.output_parsed


def campaign_reply(campaign, user_text):
    history = list(campaign.chat_messages.order_by("-created_at")[:16])
    history.reverse()
    input_messages = [{"role": item.role, "content": item.content} for item in history]
    input_messages.append({"role": "user", "content": user_text})
    profile = CandidateProfile.objects.filter(pk=1).first()
    profile_text = (profile.profile_draft or profile.long_description)[:6000] if profile else "Not completed"
    response = _client().responses.parse(
        model=settings.OPENAI_CHAT_MODEL,
        instructions=ROBERT_RULES + """
Help define one reusable job-search campaign through conversation. Accept vague preferences and ask ONE high-value question at a time.
Separate hard requirements from soft preferences. Keep the search broad enough to notice unexpectedly strong companies and CV-building work.
When there is enough information, set ready=true and return a complete set of concise editable campaign fields. Otherwise return useful known fields too.
Do not silently turn a preference into a rejection rule.
""" + f"\nCandidate profile:\n{profile_text}\nExisting campaign brief:\n{campaign.natural_language_brief[:6000]}",
        input=input_messages,
        text_format=CampaignTurn,
        max_output_tokens=1000,
        store=False,
    )
    _record_text_usage(response, "campaign")
    return response.output_parsed


def transcribe(uploaded_file, duration_seconds=0):
    client = _client()
    result = client.audio.transcriptions.create(
        model=settings.OPENAI_TRANSCRIBE_MODEL,
        file=(uploaded_file.name or "dictation.webm", uploaded_file.read(), uploaded_file.content_type),
        response_format="text",
    )
    minutes = Decimal(str(max(float(duration_seconds or 0), 1))) / Decimal("60")
    AIUsage.objects.create(purpose="dictation", estimated_cost_usd=minutes * Decimal("0.0045"))
    return result if isinstance(result, str) else result.text
