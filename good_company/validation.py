"""Bounded JSON shape checks before opening or mutating private state."""
MAX_REQUEST_BYTES = 2_000_000


class RequestError(ValueError):
    pass


def validate_unique_recipients(addresses):
    if any(not isinstance(address, str) for address in addresses):
        raise ValueError('Recipients must be email address strings.')
    if len({address.casefold() for address in addresses}) != len(addresses):
        raise ValueError('Duplicate recipient identities are not allowed.')


def validate_signup_mode(task):
    if type(task.get('signup_required', False)) is not bool:
        raise ValueError('signup_required must be boolean; review and replace the invalid task.')


def validate_request(request):
    if not isinstance(request, dict):
        raise RequestError('Request must be a JSON object.')
    objects = {'profile', 'policy', 'snapshot', 'volunteer', 'task', 'message', 'rule', 'preferences', 'metadata', 'proposed'}
    string_lists = {'roles', 'eligible_roles', 'preferred_skills', 'avoid_categories', 'preferred_categories',
                    'calendar_scopes', 'allowed_event_types', 'allowed_task_categories', 'allowed_recipients',
                    'reminder_recipients', 'to', 'bcc', 'detail_sources', 'required_credentials', 'channels', 'categories', 'sources', 'missing'}
    integer_lists = {'reminder_days', 'cadence_days', 'task_reminder_hours'}
    object_lists = {'events', 'rules', 'availability', 'busy'}
    booleans = {'enabled', 'apply', 'complete', 'all_day', 'mixed_role_audience', 'accepts_delegation', 'signup_required'}
    scalars = {'organization', 'timezone', 'greeting', 'signoff', 'audience', 'sender', 'source', 'title', 'updated',
               'authority', 'question', 'calendar', 'window_start', 'window_end', 'checked_at', 'id', 'start', 'end',
               'status', 'event_type', 'dress_code_role', 'dress_applicability', 'program', 'location', 'attire',
               'bring', 'meal', 'arrival', 'rsvp', 'rid', 'notice_id', 'task_id', 'volunteer_id', 'assignment_id',
               'correction_id', 'original_id', 'event_id', 'outcome', 'provider_id', 'expected_hash', 'name', 'email',
               'category', 'role_match', 'role', 'section', 'version', 'issuing_body', 'effective_from', 'effective_until',
               'valid_from', 'valid_until', 'issuer', 'review_by', 'original_source', 'review_authority', 'address', 'component', 'evidence', 'note', 'before',
               'subject', 'body', 'on', 'kind', 'preferred_source', 'overridden_source', 'evidence_source'}
    integers = {'send_hour', 'max_reminders_per_day', 'max_open_tasks', 'quiet_start', 'quiet_end', 'min_interval_hours'}
    total = 0

    def walk(value, depth=0, field='request'):
        nonlocal total
        total += 1
        if total > 30000 or depth > 12:
            raise RequestError('Request exceeds nesting or element limits.')
        if isinstance(value, str):
            if len(value) > (1_000_000 if field == 'text' else 65536):
                raise RequestError('A text field exceeds its supported size.')
            return
        if isinstance(value, dict):
            if len(value) > 1000:
                raise RequestError('An object has too many fields.')
            for key, child in value.items():
                if not isinstance(key, str) or len(key) > 256:
                    raise RequestError('Object field names must be bounded strings.')
                if field in ('skills', 'required_skills', 'recipient_roles', 'program_audiences', 'terminology'):
                    walk(child, depth + 1, key)
                    continue
                if key in objects and child is not None and not isinstance(child, dict):
                    raise RequestError('A nested object has the wrong type.')
                if key in string_lists and (not isinstance(child, list) or any(not isinstance(x, str) for x in child)):
                    raise RequestError('A string-list field has the wrong type.')
                if key in integer_lists and (not isinstance(child, list) or any(type(x) is not int for x in child)):
                    raise RequestError('An integer-list field has the wrong type.')
                if key in object_lists and (not isinstance(child, list) or any(not isinstance(x, dict) for x in child)):
                    raise RequestError('An object-list field has the wrong type.')
                if key in booleans and type(child) is not bool:
                    raise RequestError('A boolean field has the wrong type.')
                if key in integers and type(child) is not int:
                    raise RequestError('An integer field has the wrong type.')
                if key in scalars and child is not None and not isinstance(child, str):
                    raise RequestError('A string field has the wrong type.')
                if key in ('skills', 'required_skills') and (not isinstance(child, dict) or any(type(x) is not int for x in child.values())):
                    raise RequestError('Skill levels must be an object of integers.')
                if key == 'program_audiences' and (not isinstance(child, dict) or any(not isinstance(x, list) or any(not isinstance(a, str) for a in x) for x in child.values())):
                    raise RequestError('Program audiences must map names to address lists.')
                if key == 'recipient_roles' and (not isinstance(child, dict) or any(not isinstance(x, str) for x in child.values())):
                    raise RequestError('Recipient roles must map addresses to role strings.')
                if key == 'credentials' and (not isinstance(child, list) or any(not isinstance(x, dict) for x in child)):
                    raise RequestError('Credentials must be a list of objects.')
                walk(child, depth + 1, key)
        elif isinstance(value, list):
            if len(value) > 10000:
                raise RequestError('An array has too many elements.')
            for child in value:
                walk(child, depth + 1, field)
        elif value is not None and type(value) not in (bool, int, float):
            raise RequestError('Unsupported JSON value.')
    walk(request)


def safe_error(error, request):
    if isinstance(error, OSError):
        return 'Unable to access the requested input or state file.'
    if isinstance(error, RequestError):
        return str(error)
    # Parsing and domain errors can echo a malformed date/path/value. Do not copy
    # user-supplied values into the error channel.
    detail = str(error)
    def redact(value):
        nonlocal detail
        if isinstance(value, str) and len(value) >= 4:
            detail = detail.replace(value, '[value]')
        elif isinstance(value, dict):
            for child in value.values():
                redact(child)
        elif isinstance(value, list):
            for child in value:
                redact(child)
    try:
        redact(request)
    except RecursionError:
        return 'Request nesting exceeds the supported limit.'
    return detail[:500]


SETTINGS_FIELDS = {
    'profile': frozenset({'organization', 'timezone', 'greeting', 'signoff',
        'audience', 'reminder_days', 'send_hour', 'locale', 'terminology'}),
    'policy': frozenset({'enabled', 'sender', 'calendar_scopes', 'allowed_event_types',
        'allowed_task_categories', 'allowed_recipients', 'reminder_recipients',
        'cadence_days', 'task_reminder_hours', 'max_reminders_per_day',
        'recipient_roles', 'program_audiences', 'event_contexts'}),
}


def validate_settings_fields(value, kind):
    # Silently retained lookalike settings can misrepresent sending authority,
    # pause state or limits to the owner even though the engine ignores them.
    if not isinstance(value, dict) or set(value) - SETTINGS_FIELDS[kind]:
        raise RequestError('Unsupported ' + kind + ' fields. Supported fields: '
                           + ', '.join(sorted(SETTINGS_FIELDS[kind])) + '.')
