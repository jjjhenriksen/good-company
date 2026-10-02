from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from module_fixture import NOW, coordinator, observation, policy, relationship


class RelationshipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = coordinator(Path(self.tmp.name) / 'state.sqlite', 'relationships', 'fictional-relationship-register')
        self.c.add_relationship(relationship(), 'owner', 'verified separate consent', now=NOW)

    def tearDown(self):
        self.c.db.close(); self.tmp.cleanup()

    def sync(self, snapshot=None):
        return self.c.sync_relationship('donor-one', snapshot or observation(), 'owner', 'authorized source read', now=NOW)

    def status(self):
        return self.c.module_status('relationships', 'donor-one', 'alex', now=NOW)

    def register_file(self, entries):
        path = Path(self.tmp.name) / 'register.json'
        path.write_text(json.dumps({'source': 'fictional-relationship-register', 'complete': True, 'records': entries}))
        path.chmod(0o600)
        return str(path)

    def test_exact_source_binding_records_observation_and_deduplicates(self):
        first = self.sync(observation() | {'amount_minor': 2500, 'currency': 'USD'})
        second = self.sync(observation() | {'amount_minor': 2500, 'currency': 'USD'})
        self.assertEqual(first['status'], 'source_recorded')
        self.assertTrue(second['replayed'])
        self.assertEqual(first['revision'], second['revision'])
        self.assertEqual(self.status()['record']['observation']['amount_minor'], 2500)
        self.assertNotIn('payment', self.status()['record'])

    def test_retail_payment_case_and_private_fields_are_rejected(self):
        for change in ({'state': 'retail_sale'}, {'state': 'payment_completed'}, {'case_notes': 'excluded'},
                       {'medical_record': 'excluded'}, {'amount_minor': True, 'currency': 'USD'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.sync(observation() | change)
        with self.assertRaises(ValueError):
            self.c.add_relationship(relationship() | {'id': 'sale', 'kind': 'purchaser'}, 'owner', 'invalid', now=NOW)

    def test_beneficiary_source_confirmation_is_not_case_management(self):
        self.c.add_relationship(relationship('beneficiary'), 'owner', 'separate service consent', now=NOW)
        result = self.c.sync_relationship('beneficiary-one', observation('beneficiary', 'confirmed'),
                                          'owner', 'service register acknowledgment', now=NOW)
        self.assertEqual(result['status'], 'source_confirmed')
        with self.assertRaises(ValueError):
            self.c.sync_relationship('beneficiary-one', observation('beneficiary', 'grant_approved'),
                                      'owner', 'invalid case action', now=NOW)

    def test_volunteer_and_other_record_permissions_do_not_grant_access(self):
        with self.assertRaises(ValueError):
            self.c.module_status('relationships', 'donor-one', 'sam', now=NOW)
        with self.assertRaises(ValueError):
            self.c.sync_relationship('donor-one', observation(), 'alex', 'not a source owner', now=NOW)
        for change in ({'source': 'unapproved-crm'}, {'external_id': 'another-person'}, {'kind': 'beneficiary'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.sync(observation() | change)

    def test_stale_future_conflicting_versions_and_duplicate_bindings_are_rejected(self):
        for checked in (NOW - timedelta(minutes=16), NOW + timedelta(seconds=1)):
            with self.assertRaises(ValueError):
                self.sync(observation() | {'checked_at': checked.isoformat()})
        self.sync()
        with self.assertRaises(ValueError):
            self.sync(observation(state='pledged'))
        with self.assertRaises(ValueError):
            self.c.add_relationship(relationship() | {'id': 'duplicate'}, 'owner', 'invalid duplicate', now=NOW)

    def test_private_register_import_is_atomic_repeatable_and_read_only(self):
        path = self.register_file([{'record_id': 'donor-one', 'snapshot': observation()}])
        original = Path(path).read_bytes()
        self.assertEqual(self.c.import_relationship_register(path, 'owner', 'register read', now=NOW)['imported'], 1)
        self.assertEqual(self.c.import_relationship_register(path, 'owner', 'register read', now=NOW)['replayed'], 1)
        self.assertEqual(Path(path).read_bytes(), original)
        Path(path).chmod(0o644)
        with self.assertRaises(ValueError):
            self.c.import_relationship_register(path, 'owner', 'unsafe file', now=NOW)

    def test_invalid_later_register_row_rolls_back_earlier_observation(self):
        path = self.register_file([{'record_id': 'donor-one', 'snapshot': observation()},
                                   {'record_id': 'nonexistent', 'snapshot': observation()}])
        with self.assertRaises(ValueError):
            self.c.import_relationship_register(path, 'owner', 'invalid batch', now=NOW)
        self.assertEqual(self.status()['status'], 'active')

    def test_withdrawal_works_while_paused_and_prevents_reimport(self):
        p = policy('fictional-relationship-register'); p['enabled'] = False
        self.c.configure_module('relationships', p, 'owner pause', now=NOW)
        result = self.c.withdraw_module_record('relationships', 'donor-one', 'alex', 'verified withdrawal', now=NOW)
        self.assertEqual(result['status'], 'withdrawn')
        p['enabled'] = True
        self.c.configure_module('relationships', p, 'resume', now=NOW)
        self.assertNotIn('purpose', self.status()['record'])
        with self.assertRaises(ValueError):
            self.sync()
        with self.assertRaises(ValueError):
            self.c.add_relationship(relationship(), 'owner', 'replayed old consent', now=NOW)

    def test_status_delivery_never_records_a_donation(self):
        notice = self.c.module_notice('relationships', 'donor-one', 'alex@example.invalid', NOW.isoformat(),
                                      'owner', 'separate notice authority', now=NOW)['id']
        self.c.module_claim(notice, now=NOW)
        self.c.module_receipt(notice, 'sent', 'fictional-delivery-receipt', now=NOW)
        self.assertEqual(self.status()['status'], 'active')
        self.assertNotIn('observation', self.status()['record'])

    def test_superseded_source_version_cannot_replay_a_new_notice(self):
        self.sync()
        self.sync(observation(state='pledged') | {'version': 'v2'})
        with self.assertRaises(ValueError):
            self.sync()

    def test_nonowner_import_is_refused_before_any_file_read(self):
        with patch('good_company.relationships.Path.open', side_effect=AssertionError('must not read')), self.assertRaises(ValueError):
            self.c.import_relationship_register('/private/operator-register.json', 'alex', 'not authorized', now=NOW)
