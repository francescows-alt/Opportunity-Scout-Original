from django import template
from django.utils.safestring import mark_safe

register = template.Library()


# Small, consistent line icons (20x20 viewBox, currentColor) that replace the ad hoc
# Unicode glyphs (⌖ ◫ ▶ 文 あ ✈ ...) that used to be scattered through the templates.
ICONS = {
    "nav-applications": '<rect x="3" y="3" width="6" height="6" rx="1"/><rect x="11" y="3" width="6" height="6" rx="1"/><rect x="3" y="11" width="6" height="6" rx="1"/><rect x="11" y="11" width="6" height="6" rx="1"/>',
    "nav-inbox": '<path d="M3 11l2-6h10l2 6"/><path d="M3 11v4a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-4"/><path d="M3 11h4l1 2h4l1-2h4"/>',
    "nav-profile": '<circle cx="10" cy="7" r="3.2"/><path d="M4 17c0-3.5 2.7-6 6-6s6 2.5 6 6"/>',
    "nav-rules": '<line x1="4" y1="5" x2="16" y2="5"/><line x1="4" y1="10" x2="16" y2="10"/><line x1="4" y1="15" x2="16" y2="15"/><circle cx="7" cy="5" r="1.3" fill="currentColor" stroke="none"/><circle cx="13" cy="10" r="1.3" fill="currentColor" stroke="none"/><circle cx="9" cy="15" r="1.3" fill="currentColor" stroke="none"/>',
    "location": '<path d="M10 18C10 18 4.2 11.8 4.2 7.6a5.8 5.8 0 0 1 11.6 0C15.8 11.8 10 18 10 18Z"/><circle cx="10" cy="7.6" r="2.1" fill="currentColor" stroke="none"/>',
    "building": '<rect x="5" y="3" width="10" height="15" rx="1"/><rect x="7.2" y="6" width="1.8" height="1.8"/><rect x="11" y="6" width="1.8" height="1.8"/><rect x="7.2" y="10" width="1.8" height="1.8"/><rect x="11" y="10" width="1.8" height="1.8"/><rect x="8" y="14" width="4" height="4"/>',
    "calendar": '<rect x="3" y="4.5" width="14" height="12.5" rx="1.5"/><line x1="3" y1="8.5" x2="17" y2="8.5"/><line x1="7" y1="2.5" x2="7" y2="5.5"/><line x1="13" y1="2.5" x2="13" y2="5.5"/>',
    "clock": '<circle cx="10" cy="10" r="7.3"/><path d="M10 6v4l2.8 1.8"/>',
    "alarm": '<circle cx="10" cy="10.5" r="6.8"/><path d="M10 7v3.5l2.4 1.6"/><path d="M5.3 3.6 3.4 5.5M14.7 3.6l1.9 1.9"/>',
    "language": '<path d="M4 5h12a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H9.5L6 17v-3H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z"/>',
    "globe": '<circle cx="10" cy="10" r="7.3"/><ellipse cx="10" cy="10" rx="3.1" ry="7.3"/><line x1="2.7" y1="10" x2="17.3" y2="10"/>',
    "plane": '<path d="M17.5 2.5 2.7 9.2l5.3 1.8 1.8 5.3 7.7-13.8Z"/><path d="M8 11l9.5-8.5"/>',
    "book": '<path d="M10 5.3C8.2 3.9 5.4 3.4 3.3 3.9v11.3c2.1-0.5 4.9 0 6.7 1.4V5.3Z"/><path d="M10 5.3c1.8-1.4 4.6-1.9 6.7-1.4v11.3c-2.1-0.5-4.9 0-6.7 1.4V5.3Z"/>',
    "coin": '<circle cx="10" cy="10" r="7.3"/><circle cx="10" cy="10" r="3.4"/>',
    "no-entry": '<circle cx="10" cy="10" r="7.3"/><line x1="4.9" y1="15.1" x2="15.1" y2="4.9"/>',
    "people": '<circle cx="7.3" cy="7.8" r="2.9"/><circle cx="13.2" cy="8.8" r="2.2"/><path d="M2.6 16.5c0-2.9 2.3-4.9 4.7-4.9s4.7 2 4.7 4.9"/><path d="M11.8 12.1c1.9 0 3.7 1.4 4 4.4"/>',
    "tag": '<path d="M10 3.2h4.8a1 1 0 0 1 1 1v4.8L8.7 16.1 2.9 10.3 10 3.2Z"/><circle cx="12.3" cy="6.7" r="1" fill="currentColor" stroke="none"/>',
}


@register.simple_tag
def icon(name, size=18):
    inner = ICONS.get(name)
    if not inner:
        return ""
    svg = (
        f'<svg class="icon icon-{name}" width="{size}" height="{size}" viewBox="0 0 20 20" '
        'fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true" focusable="false">{inner}</svg>'
    )
    return mark_safe(svg)
