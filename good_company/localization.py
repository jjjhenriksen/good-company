"""Explicit supported English locales; never infer organization structure."""
from zoneinfo import ZoneInfo
from .core import stamp


def validate_profile(profile):
    if profile.get('locale', 'en-US') not in ('en-US', 'en-GB'):
        raise ValueError('Supported locales are en-US and en-GB; other languages need reviewed translations.')
    terms = profile.get('terminology', {})
    if not isinstance(terms, dict) or set(terms) - {'coordinator', 'participant', 'volunteer', 'event', 'task'}:
        raise ValueError('Terminology supports coordinator, participant, volunteer, event and task.')
    if any(not isinstance(v, str) or not v.strip() or len(v) > 64 or '\n' in v for v in terms.values()):
        raise ValueError('Terms must be nonempty single-line strings of at most 64 characters.')


def term(profile, name):
    return profile.get('terminology', {}).get(name, name)


def date_text(value, profile):
    local = stamp(value).astimezone(ZoneInfo(profile['timezone']))
    pattern = '%A, %-d %B %Y' if profile.get('locale') == 'en-GB' else '%A, %B %-d, %Y'
    return local.strftime(pattern)


def time_text(value, profile):
    local = stamp(value).astimezone(ZoneInfo(profile['timezone']))
    pattern = '%H:%M' if profile.get('locale') == 'en-GB' else '%-I:%M %p'
    # Offset disambiguates repeated local times during the autumn DST transition.
    return local.strftime(pattern) + ' ' + local.strftime('%Z (UTC%z)')
