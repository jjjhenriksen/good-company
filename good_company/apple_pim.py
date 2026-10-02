"""Read-only Apple PIM boundary with exact mailbox and identity evidence binding."""
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

from .core import digest, iso, stamp
from .providers import Account, ProviderError
from .replies import VerifiedReply


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def tool_data(result, domain, action):
    """Decode one native result; marked text remains inert source data."""
    if not isinstance(result, dict) or result.get('isError') or result.get('details') != {'domain': domain, 'action': action}:
        raise ProviderError('apple_pim_invalid_envelope')
    blocks = result.get('content', [])
    if len(blocks) != 1 or blocks[0].get('type') != 'text' or not isinstance(blocks[0].get('text'), str):
        raise ProviderError('apple_pim_ambiguous_content')
    text = blocks[0]['text']
    if text.startswith('Data between [UNTRUSTED_' + domain.upper() + '_DATA_'):
        _, separator, text = text.partition('\n\n')
        if not separator:
            raise ProviderError('apple_pim_invalid_preamble')
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        raise ProviderError('apple_pim_invalid_json') from None
    if not isinstance(value, dict) or value.get('success') is False or value.get('error') or value.get('truncated') or value.get('degraded'):
        raise ProviderError('apple_pim_unconfirmed_result')
    return value


def source_text(value, domain):
    if not isinstance(value, str):
        raise ProviderError('apple_pim_missing_source_text')
    pattern = r'\[UNTRUSTED_' + domain.upper() + r'_DATA_([A-Z0-9]+)\] (.*) \[/UNTRUSTED_' + domain.upper() + r'_DATA_\1\]'
    marked = re.fullmatch(pattern, value, re.DOTALL)
    return marked[2] if marked else value


class NativeApplePIM:
    """Only scoped read actions; no send, shell, mutation or config override API."""
    def __init__(self, port, token, config_dir):
        if type(port) is not int or not 1024 <= port <= 65535 or not isinstance(token, str) or not token.strip():
            raise ProviderError('apple_pim_missing_local_connection')
        self.url, self.token = f'http://127.0.0.1:{port}/tools/invoke', token
        self.config_dir = str(Path(config_dir).expanduser().resolve(strict=True))
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)

    def __call__(self, domain, action, **arguments):
        allowed = {'mail': {'accounts', 'get', 'auth_check'}, 'calendar': {'list', 'events'}}
        if action not in allowed.get(domain, set()) or {'configDir', 'profile', 'action'} & set(arguments):
            raise ProviderError('apple_pim_read_outside_scope')
        payload = {'tool': 'apple_pim_' + domain, 'args': {'action': action, 'configDir': self.config_dir, **arguments}}
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode(),
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=15) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError()
            envelope = json.loads(raw)
            if envelope.get('ok') is not True:
                raise ValueError()
            value = tool_data(envelope['result'], domain, action)
            return value, iso(stamp())
        except Exception:
            raise ProviderError('apple_pim_read_unconfirmed') from None


def message_id(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 512 or re.search(r'[\s\x00-\x1f]', value):
        raise ProviderError('apple_pim_invalid_message_id')
    value = value[1:-1] if value.startswith('<') and value.endswith('>') else value
    if not value or '<' in value or '>' in value:
        raise ProviderError('apple_pim_invalid_message_id')
    return value


class ApplePIMReplies:
    """Requires the native identity verdict to bind the exact message and policy.

    Older Apple PIM versions omit messageBinding and are deliberately refused.
    Merely passing DKIM/SPF is insufficient to authorize a domain mutation.
    """
    def __init__(self, read, account_id, sender, mailbox, trusted_senders):
        if any(not isinstance(v, str) or not v.strip() or '\x00' in v for v in (account_id, sender, mailbox)):
            raise ProviderError('apple_pim_explicit_mailbox_required')
        if not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', sender):
            raise ProviderError('apple_pim_invalid_sender')
        self.read, self.account_id, self.sender, self.mailbox = read, account_id, sender, mailbox
        self.trusted_senders = Path(trusted_senders).expanduser().resolve(strict=True)

    def _identity(self):
        data, _ = self.read('mail', 'accounts')
        accounts = data.get('accounts')
        if not isinstance(accounts, list):
            raise ProviderError('apple_pim_missing_accounts')
        matches = [a for a in accounts if isinstance(a, dict) and a.get('id') == self.account_id]
        if len(matches) != 1 or matches[0].get('enabled') is not True or matches[0].get('userName', '').casefold() != self.sender.casefold():
            raise ProviderError('apple_pim_account_unavailable')
        name = matches[0].get('name')
        if not isinstance(name, str) or not name.strip() or sum(a.get('name') == name for a in accounts if isinstance(a, dict)) != 1:
            raise ProviderError('apple_pim_ambiguous_account_name')
        return name

    def account(self):
        self._identity()
        return Account('apple-pim', self.account_id, self.sender, True, frozenset(), False, False)

    def _policy(self):
        try:
            raw = self.trusted_senders.read_bytes()
            if len(raw) > 100_000:
                raise ValueError()
            policy = json.loads(raw)
            trusted = policy['trustedAuthservIds'].get(self.account_id)
            if not isinstance(trusted, list) or not trusted or any(not isinstance(v, str) or not v.strip() for v in trusted):
                raise ValueError()
            if not isinstance(policy['trustedSenders'], list):
                raise ValueError()
            return policy, hashlib.sha256(raw).hexdigest()
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            raise ProviderError('apple_pim_invalid_identity_policy') from None

    @staticmethod
    def command(content):
        content = source_text(content, 'mail').strip()
        match = re.fullmatch(r'(STOP|DECLINE|COMPLETE)(?: ([A-Za-z0-9_.:/-]{1,200}))?', content, re.IGNORECASE)
        if not match or ((match[1].upper() == 'STOP') != (match[2] is None)):
            raise ProviderError('apple_pim_unsupported_reply_command')
        return match[1].lower(), match[2]

    def verified_reply(self, requested_id):
        requested_id = message_id(requested_id)
        name = self._identity()
        policy, policy_hash = self._policy()
        args = {'id': requested_id, 'account': self.account_id, 'mailbox': self.mailbox}
        first, _ = self.read('mail', 'get', **args, format='plain')
        msg = first.get('message', {})
        if (not isinstance(msg, dict) or message_id(msg.get('messageId')) != requested_id
                or msg.get('account') != name or msg.get('mailbox') != self.mailbox):
            raise ProviderError('apple_pim_message_outside_mailbox')
        sender = msg.get('senderAddress')
        if not isinstance(sender, str) or not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', sender):
            raise ProviderError('apple_pim_missing_structured_sender')
        enrolled = [p for p in policy['trustedSenders'] if isinstance(p, dict)
                    and sender.casefold() in [v.casefold() for v in p.get('emails', []) if isinstance(v, str)]]
        if len(enrolled) != 1 or not isinstance(enrolled[0].get('expectedDkimDomains'), list) or not enrolled[0]['expectedDkimDomains']:
            raise ProviderError('apple_pim_sender_not_uniquely_enrolled')
        content, headers = source_text(msg.get('content'), 'mail'), msg.get('allHeaders')
        if len(content) > 4096 or not isinstance(headers, str) or not headers or len(headers) > 100_000:
            raise ProviderError('apple_pim_missing_bound_message')
        verdict, _ = self.read('mail', 'auth_check', **args, trustedSenders=str(self.trusted_senders))
        dkim = verdict.get('checks', {}).get('dkim', {})
        binding = {'messageId': requested_id, 'accountId': self.account_id, 'mailbox': self.mailbox,
                   'senderAddress': sender.casefold(), 'contentSha256': hashlib.sha256(content.encode()).hexdigest(),
                   'headersSha256': hashlib.sha256(headers.encode()).hexdigest(), 'policySha256': policy_hash}
        if (verdict.get('evaluated') is not True or verdict.get('verdict') != 'verified'
                or verdict.get('sender', '').casefold() != sender.casefold()
                or verdict.get('messageBinding') != binding or dkim.get('result') != 'pass'
                or dkim.get('match') is not True or dkim.get('expected') != enrolled[0]['expectedDkimDomains']):
            raise ProviderError('apple_pim_unbound_or_unverified_identity')
        second, _ = self.read('mail', 'get', **args, format='plain')
        if second != first or self._identity() != name or self._policy()[1] != policy_hash:
            raise ProviderError('apple_pim_identity_changed_during_read')
        action, target = self.command(content)
        return VerifiedReply(requested_id, sender.casefold(), True, 'apple-pim-identity:' + digest(binding), action, target)
