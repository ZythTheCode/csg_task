from django import template

register = template.Library()

# Common position abbreviations
ABBREVIATIONS = {
    'vice president': 'VP',
    'president': 'PRES',
    'treasurer': 'TRES',
    'auditor': 'AUD',
    'secretary': 'SEC',
    'assistant secretary': 'Asst. Sec',
    'assistant treasurer': 'Asst. Tres',
    'executive assistant': 'EA',
    'business manager': 'BM',
    'events manager': 'EM',
    'p.r.o.': 'PRO',
    'public relations officer': 'PRO',
}


@register.filter
def initials(value):
    """Convert a position title, User, or Position object to a compact abbreviation.
    Uses custom initials if defined, otherwise falls back to lookup table or acronym."""
    if not value:
        return ''
    if hasattr(value, 'position_initials'):
        return value.position_initials
    if hasattr(value, 'get_initials'):
        return value.get_initials()
    if hasattr(value, 'initials') and getattr(value, 'initials'):
        return getattr(value, 'initials')

    text = str(value).strip()
    lower = text.lower()

    # Check known abbreviations first
    if lower in ABBREVIATIONS:
        return ABBREVIATIONS[lower]

    words = text.split()
    if len(words) == 1:
        return text[:4].upper()
    return ''.join(w[0].upper() for w in words if w)


@register.simple_tag
def can_edit_task(user, task):
    return user.can_edit_task(task)


@register.simple_tag
def can_update_task_progress(user, task):
    return user.can_update_task_progress(task)
