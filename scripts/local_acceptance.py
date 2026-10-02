#!/usr/bin/env python3
"""Run reproducible fictional adoption checks without calendar or mail access."""
import argparse
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

CASES = {
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


def run():
    report = {'evidence_kind': 'fictional_library_tests', 'live_provider_acceptance': False, 'scenarios': {}}
    for scenario, names in CASES.items():
        suite = unittest.defaultTestLoader.loadTestsFromNames(names)
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        report['scenarios'][scenario] = {'passed': result.wasSuccessful(), 'checks': result.testsRun,
                                       'failed_checks': [test.id() for test, _ in result.failures + result.errors],
                                       'test_ids': names}
    report['passed'] = all(s['passed'] for s in report['scenarios'].values())
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
        with args.report.open('x') as stream:
            stream.write(output)
        args.report.chmod(0o600)
    print(output)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
