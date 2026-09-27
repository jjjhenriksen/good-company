"""Explicit owner context for exact calendar instances; never inferred from titles."""

FIELDS = {'source', 'event_type', 'dress_applicability', 'program',
          'dress_code_role', 'mixed_role_audience', 'location'}


def validate(policy):
    contexts = policy.get('event_contexts', {})
    if not isinstance(contexts, dict):
        raise ValueError('event_contexts must map authorized calendars to exact event IDs.')
    for calendar, entries in contexts.items():
        if calendar not in policy['calendar_scopes'] or not isinstance(entries, dict):
            raise ValueError('Event context must use an authorized calendar scope.')
        for uid, context in entries.items():
            if not isinstance(uid, str) or not uid.strip() or uid == '*':
                raise ValueError('Event context requires an exact instance ID.')
            if not isinstance(context, dict) or set(context) - FIELDS or not context.get('source'):
                raise ValueError('Event context requires a source and supported classification fields.')
            for field, value in context.items():
                if field == 'mixed_role_audience':
                    if type(value) is not bool:
                        raise ValueError('mixed_role_audience must be true or false.')
                elif not isinstance(value, str) or not value.strip():
                    raise ValueError('Event context values must be nonempty text.')
            if 'event_type' in context and context['event_type'] not in policy['allowed_event_types']:
                raise ValueError('Event context type must be in the standing remit.')
            if context.get('dress_applicability', 'unknown') not in ('required', 'not_applicable', 'unknown'):
                raise ValueError('Invalid owner dress applicability.')


def annotate(event, calendar, policy):
    """Preserve provider facts and attach narrowly scoped, cited owner context.

    A supplied location fills a missing location only. Calendar moves, times,
    cancellations, sources and identities can never be overridden here.
    """
    context = (policy or {}).get('event_contexts', {}).get(calendar, {}).get(event['id'])
    if not context:
        return event
    result = dict(event)
    for key, value in context.items():
        if key == 'source' or (key == 'location' and event.get('location')):
            continue
        result[key] = value
    sources = list(event.get('detail_sources', []))
    if context['source'] not in sources:
        sources.append(context['source'])
    result['detail_sources'] = sources
    return result
