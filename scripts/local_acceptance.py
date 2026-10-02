#!/usr/bin/env python3
"""Run reproducible fictional adoption checks without calendar or mail access."""
import argparse
import io
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

CASES = {
    'verified_replies_29': [
        'test_verified_replies.ReplyTests.test_verified_decline_reassigns_and_replay_is_refused',
        'test_verified_replies.ReplyTests.test_spoofed_identity_and_other_participant_cannot_mutate',
        'test_verified_replies.ReplyTests.test_unrelated_mailbox_cannot_read_or_apply_reply',
        'test_verified_replies.ReplyTests.test_missing_remit_cannot_accept_reply',
        'test_verified_replies.ReplyTests.test_account_change_during_provider_read_cannot_mutate_state',
        'test_verified_replies.ReplyTests.test_verified_stop_still_works_when_sending_is_paused',
    ],
    'signup_intake_41': [
        'test_signups.SignupTests.test_simultaneous_signups_reserve_one_and_waitlist_one',
        'test_signups.SignupTests.test_decline_reserves_qualified_replacement_and_rsvp_is_separate',
        'test_signups.SignupTests.test_decline_leaves_another_shift_reservation_intact',
        'test_signups.SignupTests.test_decline_does_not_promote_someone_who_opted_out',
        'test_signups.SignupTests.test_wrong_mailbox_or_paused_scope_never_reads_reply',
        'test_signups.SignupTests.test_mailbox_changed_during_read_does_not_apply_signup',
    ],
    'food_bank_58': [
        'test_tasks.TaskTests.test_role_constraint_is_hard',
        'test_tasks.TaskTests.test_unavailable_volunteer_is_skipped',
        'test_signups.SignupTests.test_normal_verified_decline_promotes_waitlist_without_confirming',
        'test_signups.SignupTests.test_simultaneous_signups_reserve_one_and_waitlist_one',
        'test_cycle.CycleTests.test_cycle_allocates_and_sends_assignment_once_across_ticks',
    ],
    'arts_change_59': [
        'test_program_audiences.ProgramAudienceTests.test_two_programs_have_disjoint_claims',
        'test_program_audiences.ProgramAudienceTests.test_program_move_invalidates_old_authority',
        'test_linked_tasks.LinkedTaskTests.test_change_before_assignment_yields_impact_and_no_assignment',
        'test_linked_tasks.LinkedTaskTests.test_cancel_after_attempt_preserves_history_and_blocks_pending',
        'test_corrections.CorrectionTests.test_correction_deduplicates_and_uncertain_never_retries',
    ],
    'mutual_aid_stop_60': [
        'test_verified_replies.ReplyTests.test_verified_stop_still_works_when_sending_is_paused',
        'test_verified_replies.ReplyTests.test_spoofed_identity_and_other_participant_cannot_mutate',
        'test_consent.EventConsentTests.test_stop_invalidates_queued_event_then_unaffected_recipient_can_send',
        'test_shared_budget.BudgetTests.test_event_attempt_consumes_task_budget_after_restart',
        'test_shared_budget.BudgetTests.test_concurrent_event_and_task_reservations_share_one_slot',
    ],
    'board_meeting_61': [
        'test_dress_applicability.ApplicabilityTests.test_not_applicable_can_send_without_rules',
        'test_dress_applicability.ApplicabilityTests.test_not_applicable_cannot_bypass_event_scope',
        'test_core.CoordinationTests.test_conflicts_hide_private_title',
        'test_cycle.CycleTests.test_cycle_allocates_and_sends_assignment_once_across_ticks',
    ],
}

# Local checks prepare evidence; they cannot supply a real identity, receipt or pilot.
REMAINING = {
    29: ('integration', 'Mailbox-bound genuine and spoofed replies through the same verified provider bridge.'),
    31: ('integration', 'Complete recurring calendar identity, permissions and mail receipt/reconciliation contract.'),
    41: ('integration', 'Live verified signup/decline/acceptance through the #29 provider bridge.'),
    46: ('pilot_discovery', 'Actual resource inventory, ownership, booking/conflict authority and retention.'),
    47: ('pilot_discovery', 'Actual accessibility intake/fulfillment owner, consent, access and retention.'),
    48: ('pilot_discovery', 'Supplied forms/deadlines, authoritative status, access and reminder remit.'),
    49: ('pilot_discovery', 'Specific donor/beneficiary workflow and system, minimal data and authority.'),
    58: ('live_scenario', 'Authorized mailbox and genuine shift eligibility/decline/replacement evidence.'),
    59: ('live_scenario', 'Controlled event changes, team-specific receipts and no leakage or duplicates.'),
    60: ('live_scenario', 'Verified live STOP across pending workflows while unaffected work continues.'),
    61: ('live_scenario', 'Scoped board reminder with private conflict and real receipt/deduplication.'),
}

COMPLETED = {
    '16': {'accepted': True, 'evidence_kind': 'owner_confirmation', 'date': '2026-10-01',
           'basis': 'Owner confirmed fresh-user installation is proven with one-click installation allowed.'},
}


def issue_status(scenarios):
    return {str(number): {
        'category': category, 'accepted': False, 'remaining': requirement,
        'local_checks_passed': next((value['passed'] for name, value in scenarios.items()
                                     if name.endswith('_' + str(number))), None),
    } for number, (category, requirement) in REMAINING.items()}


def run():
    report = {'evidence_kind': 'fictional_library_tests', 'live_provider_acceptance': False, 'scenarios': {}}
    for scenario, names in CASES.items():
        suite = unittest.defaultTestLoader.loadTestsFromNames(names)
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        report['scenarios'][scenario] = {'passed': result.wasSuccessful(), 'checks': result.testsRun,
                                       'failed_checks': [test.id() for test, _ in result.failures + result.errors],
                                       'test_ids': names}
    report['passed'] = all(s['passed'] for s in report['scenarios'].values())
    report['issues'] = issue_status(report['scenarios'])
    report['completed_issues'] = COMPLETED
    report['remaining_issue_acceptance'] = False
    report['remaining'] = 'Authorized test calendar/mailbox, provider identity proofs, genuine receipts and same-path live runs.'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = run()
    output = json.dumps(report, indent=2) + '\n'
    if args.report:
        # A report is reproducible evidence, never authority to enable a sender.
        with os.fdopen(os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            stream.write(output)
    print(output)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
