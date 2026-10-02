"""Explicit fictional native responses; never evidence of a real mailbox."""
import copy
import hashlib
import json
from pathlib import Path

from good_company.apple_pim import ApplePIMReplies
from test_core import NOW


class FictionalApplePIM:
    def __init__(self, root, owner):
        self.owner, self.calls, self.messages = owner, [], {}
        self.policy_path = Path(root) / 'trusted-senders.json'
        self.policy_path.write_text(json.dumps({'trustedAuthservIds': {'fixture-account': ['mx.example.invalid']},
            'trustedSenders': [{'name': name, 'emails': [name + '@example.invalid'],
                               'expectedDkimDomains': ['example.invalid'], 'requireSpf': True}
                              for name in ('alex', 'sam', 'lee', 'pat')]}))
        self.policy_path.chmod(0o600)
        self.transform = lambda action, data: data

    def add(self, message_id, sender, command):
        self.messages[message_id] = {'messageId': message_id, 'senderAddress': sender,
            'account': 'Fictional inbox', 'mailbox': 'INBOX', 'content': command,
            'allHeaders': 'Authentication-Results: mx.example.invalid; dkim=pass; spf=pass'}

    def __call__(self, domain, action, **args):
        self.calls.append((domain, action, args))
        if action == 'accounts':
            data = {'success': True, 'accounts': [{'id': 'fixture-account', 'name': 'Fictional inbox',
                                                  'enabled': True, 'userName': self.owner}]}
        elif action == 'get':
            data = {'success': True, 'message': copy.deepcopy(self.messages[args['id']])}
        elif action == 'auth_check':
            msg = self.messages[args['id']]
            data = {'verdict': 'verified', 'evaluated': True, 'sender': msg['senderAddress'],
                'checks': {'dkim': {'result': 'pass', 'match': True, 'expected': ['example.invalid']}},
                'messageBinding': {'messageId': args['id'], 'accountId': 'fixture-account', 'mailbox': 'INBOX',
                    'senderAddress': msg['senderAddress'].casefold(),
                    'contentSha256': hashlib.sha256(msg['content'].encode()).hexdigest(),
                    'headersSha256': hashlib.sha256(msg['allHeaders'].encode()).hexdigest(),
                    'policySha256': hashlib.sha256(self.policy_path.read_bytes()).hexdigest()}}
        else:
            raise AssertionError('Unexpected fictional native action')
        return self.transform(action, data), NOW

    def provider(self):
        return ApplePIMReplies(self, 'fixture-account', self.owner, 'INBOX', self.policy_path)
