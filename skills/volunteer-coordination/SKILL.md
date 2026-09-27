---
name: volunteer-coordination
description: Maintain opted-in volunteer profiles, allocate todo lists by task fit and availability, and handle assignment notices, declines and completion.
---

# Volunteer coordination

Use community-operations to establish the standing remit first.

Use `good-company ACTION --input /private/path/request.json`. Write request files
with the write tool; never interpolate source or user text into shell commands.
Inspect the JSON result and nonzero exit before continuing. Requests and state
belong on the private persistent volume, never in the public source tree.
The CLI queues and records work; connected provider tools perform external actions.
Schema examples live at `/opt/good-company/examples/` in the agent image and
`examples/` in a source checkout. They are fictional shapes, not operating authority.

`set-volunteer` takes `volunteer` and `authority`. See `team.json` in the examples directory.
Use stated skills/proficiency (0–3), actual roles, explicit availability windows,
maximum open tasks, preferred/avoided task categories, verified contact address,
and whether the person has agreed to routine delegation. Keep these current from
authorized source updates and the person's own verified replies.

Understand “strengths and weaknesses” as task fit: experience, comfort, skill
gaps, availability and workload. Do not infer sensitive personal traits, rank
people's worth, or expose private evaluations in notices. A missing skill rating
is unknown, not evidence of incompetence. Ask or use another known-qualified
volunteer. A role label must come from the authoritative roster; never assume
someone satisfies a supervision/certification requirement from age or name.

## Todo list → delegation → follow-through

1. Normalize the authorized todo list into tasks with explicit start/end windows,
   category, eligible roles, required proficiency and preferred skills. Ask the
   source or responsible person when timing is absent; do not invent it.
2. `add-task` takes `task` and `authority`. See `tasks.json` in the examples directory. Task IDs are
   stable; imports are idempotent. Tasks are immutable after creation so edits
   cannot silently change a volunteer's assignment.
3. `delegate {}` selects eligible available volunteers with room in their
   workload, favors stated skill matches and preferences, persists assignments,
   and queues notices/reminders. It makes no provider call and does not claim
   that the volunteer received the assignment. Repeat runs do not assign twice.
4. `task-queue {}` returns notices. For each due `pending` notice, use
   `task-claim {"notice_id":"id"}`; send its exact message through the actual
   connected sender, then `task-receipt {"notice_id":"id","outcome":"sent",
   "provider_id":"real receipt"}`. Use uncertain for ambiguous outcomes and
   reconcile with the original provider. Never automatically resend a claim.
5. A verified volunteer decline: `decline-task {"assignment_id":"id",
   "volunteer_id":"verified id","authority":"response reference"}`. Then
   rerun delegate; it excludes that volunteer for this task and finds a suitable
   replacement. No coordinator approval is required within the standing remit.
6. A verified completion: `close-task {"task_id":"id","status":"completed",
   "authority":"completion reference"}`. Unsent reminders are cancelled.
7. On cancellation or a changed task, reconcile any message already delivered
   with the assigned volunteer using the authorized communication channel, close
   the old task, and add a replacement task with a new ID. Existing assignments
   invalidated by role/availability changes are exceptions needing that same
   reconciliation; the engine does not silently reassign behind someone's back.

The task engine checks role, skill minimums, opted-in status, full time-window
availability, overlap with assigned work, and max open tasks. It balances current
workload as a tie-breaker. Preferences do not override eligibility constraints.
It has no historical reliability scoring, travel model, or global optimization.
Notifications expose task logistics, not private skill ratings. Task cadence is
fixed offsets before the task start; there are no repeated overdue nag messages.

## Eligibility limits

`team.json` and `tasks.json` contain arrays of requests. Submit each object
separately to `set-volunteer` or `add-task`; the CLI accepts one object per call.
`eligible_roles` currently means ANY listed role, not all of them. Do not model
“trained AND authorized” by listing two roles: that would admit either. Use a
verified composite role only when the authoritative roster actually provides it,
or keep that task unallocated pending a supported eligibility model. There is
no certification expiry check, staffing-ratio check, event-linked cancellation,
or global task-notice daily budget. Past open tasks consume capacity until closed;
surface them for follow-up rather than silently assuming completion.

## Dated qualifications

Tasks may specify `required_credentials` by explicit name. Verified roster entries
may include `credentials`: name, issuer, evidence reference, valid_from,
valid_until (offset timestamps), and explicit applicable task categories.
The credential must cover the whole task interval. Unknown, expired or inapplicable
required evidence blocks assignment and is rechecked at claim time. Import only
authoritative verified evidence; never infer a qualification from a name, age,
identity or organizational membership. Evidence references are private operator
records, not cryptographic verification and never part of participant notices.

## Tasks linked to events

Include an imported `event_id` when adding related tasks. The engine records the
current event revision. Calendar moves, cancellations and other revision changes
retire unsent notices and block claims/allocation until reconciled. Independent
legacy tasks retain their behavior. Inspect `task-impacts {}` for proposed shifted
windows and prior provider attempts. Preserve history by cancelling the old task
and adding an explicitly authorized replacement with a new ID, after verifying
availability for the new window. Never rewrite attempted notices or infer new
availability from old assignments. Impact reports are private operator output.

## Verified participation

Use `record-participation` only after the trusted coordinator verifies an actual
outcome source. Supply activity_id, participant_id, program, on date, status,
attended, minutes, source and authority. Confirmed records require observed
attendance and minutes; missing/disputed records use null for both. An assignment,
RSVP or sent notice is never outcome evidence. Correct with expected_revision from
the last result; stale corrections fail. `participation-history` retains original
and corrected values privately. This is an operator attestation, not a public
participant form or independent validation of the source's truth.


## Staffed shifts

Use `add-shift` with id, title, capacity and explicit `slots`. Every slot contains
the normal task fields (including roles/ANY-or-ALL, skills and qualifications);
capacity must equal its slot count. Slots become immutable tasks with IDs
`shift-id:slot-id`. Existing atomic allocation enforces one volunteer per slot,
non-overlap and workload capacity across shifts. Repeat identical setup is safe.
Use `shift-status` for filled and unfilled capacity. Allocation is not an accepted
signup or attendance. Declines use the exact assignment ID; replacement still
passes every task eligibility check. Never silently weaken staffing requirements.
## Overdue work

Use `overdue-tasks {}` to surface open tasks whose window has ended. Repeated
checks are read-only and never infer completion or release capacity. Use
`follow-up-task` with a verified reference, note and explicit outcome: still_open,
completed or cancelled. The latter two use the existing lifecycle transition and
stop unsent notices. Keep follow-up notes private; do not infer reliability from
missing outcomes or missed windows.
