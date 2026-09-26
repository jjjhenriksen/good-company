---
name: event-coordination
description: Import scoped calendars, find scheduling conflicts, prepare event reminders, and track authorized delivery and corrections.
---

# Event coordination

Use community-operations for profile, standing remit and the scheduler.

Use `good-company ACTION --input /private/path/request.json`. Write request files
with the write tool; never interpolate source or user text into shell commands.
Inspect the JSON result and nonzero exit before continuing. Requests and state
belong on the private persistent volume, never in the public source tree.
The CLI queues and records work; connected provider tools perform external actions.
Schema examples live at `/opt/good-company/examples/` in the agent image and
`examples/` in a source checkout. They are fictional shapes, not operating authority.

## Calendar import

Read the inherited google-workspace skill and the connected Mac's current skills.
Use the tools actually present. If the pilot's calendar is Apple/iCloud rather
than Google, use an available owner-authorized Apple Calendar capability; do not
pretend Google access covers it. If no connector exists, ask for a scoped export
and label it a snapshot, not an automatically refreshing connection.

Read all pages of a defined date range, expand recurrence, and preserve each
provider occurrence ID. A series master is not an occurrence. Calendar fields
supply time/location; an event guide may supply attire/meals/RSVP. If they disagree,
mark the event tentative and resolve the conflict from an authoritative source
or responsible person before authorizing the reminder. Escalate only unresolved conflicts.
Keep source links for enriched details. Exclude unrelated personal events. A named
scope must always use the same event-selection rule; changing the rule needs a
new scope. Import-only snapshots are NOT automatic calendar synchronization.

`import-calendar`: `{ "snapshot": {"calendar":"verified-account/calendar/organization-scope",
"complete":true, "window_start":"2026-09-25T00:00:00-07:00",
"window_end":"2026-10-25T00:00:00-07:00", "checked_at":"ACTUAL_FETCH_TIME_WITH_OFFSET",
"events":[{"id":"provider-occurrence-id", "title":"Community dinner",
"start":"2026-10-02T17:30:00-07:00", "end":"2026-10-02T19:00:00-07:00",
"location":"Verified venue", "status":"confirmed", "source":"calendar-source",
"detail_sources":["event-guide URL, page 4"], "rsvp":"Verified RSVP instructions"}] } }`.
Optional detail fields: attire, bring, meal, arrival, rsvp. All-day events use
`all_day:true` and a date-only start; they cannot be approved until time is resolved.
Snapshot omissions within its window cancel stored instances. Never mark partial,
failed, truncated, title-search-only results complete. Window limit is 93 days.
Use complete smaller windows when needed. Do not fabricate an end time; request
it or import the documented all-day placeholder for draft-only planning.

`events`: `{}`. `plan`: `{}`. `queue`: `{}`.
Planning is idempotent. Without standing instructions it creates drafts; with
enabled standing instructions it also automatically authorizes complete sourced
templates within the configured scope. It does not send or set a scheduler.
Changed events invalidate old unsent approvals. Source-enrichment changes count
as event changes. Review any already-sent stale notice and propose an explicit
correction; the software does not send corrections automatically.

## Review and delivery

Steps 1–3 are for explicitly authorized exceptional correspondence. Routine
canonical reminders use autonomous `plan` authorization and proceed to steps
4–6; do not ask for per-message approval within the standing remit.

1. `review`: `{ "rid":"reminder id" }`. Show the owner recipients, subject, body,
   send time, source citations, and missing fields. Default recipients are empty.
2. `edit`: `{ "rid":"id", "message":{...complete reviewed message object...} }`.
   Set explicit `to`/`bcc` address arrays. Keep sources. Resolve `missing` only with
   evidence. Use the organization's established voice. Any edit clears approval.
3. After actual owner authorization, `approve`: `{ "rid":"id",
   "expected_hash":"review_hash", "authority":"actual owner message reference" }`.
   Do not manufacture authorization references. The CLI trusts the local operator;
   the reference is audit evidence, not cryptographic identity verification.
4. At the due time, FIRST refresh the calendar and import the unchanged complete
   scope. Calendar freshness must be at most 15 minutes. Recheck changed event-guide
   details too. Verify the connected sender is available before claiming.
5. `claim`: `{ "rid":"id" }`. A successful result authorizes one attempt using
   the exact approved fields. Immediately send through the documented connected
   mail tool. Do not alter content after claiming. Never claim a second time.
6. `receipt`: `{ "rid":"id", "outcome":"sent", "provider_id":"actual receipt" }`.
   Use `uncertain` for timeout/ambiguous delivery and `failed` only when the tool
   definitively reports no send. A claimed item left by a crash must be reconciled
   with the provider; it is never automatically retried. `sent` means the provider
   accepted it, not that a person read it. Do not record synthetic receipts in a
   live database. Example/test receipts belong only in the demo database.

## Autonomous delivery

`plan` authorizes complete canonical templates within standing scope; an
`approved` item with `mode: autonomous` records that policy authorization, not
per-message human review. Use the due-time refresh, claim and receipt steps above
without a manual approve call. Send through the claim’s exact `sender` account,
preserve BCC and all message fields, and record only the real provider result.
If the provider requires interactive approval each time, unattended delivery is
unavailable on that connection. Continue preparing drafts and report the limit.

Current limitation: autonomous scope needs `event_type`, but every typed event
also triggers the dress resolver. Even an online meeting without a dress policy
will remain blocked unless applicable rules exist. Do not fabricate a dress rule,
remove the event category or manually clear missing fields to bypass this gap.
One instance supports one event audience and one dress role per event. Do not
promise automatic per-team or mixed-role messages; these require a later feature.

## Calendar executive assistance

`conflicts`: `{ "proposed":{"start":"ISO+offset","end":"ISO+offset"},
"busy":[{"start":"ISO+offset","end":"ISO+offset"}] }`.
Fetch current busy intervals from the actual calendars first; include the owner's
travel buffers. This helper only compares supplied intervals and does not book.
When the owner authorizes a booking, use the real connected calendar tool, verify
its returned event id and time, and report it. Preserve attendee and series
semantics. Never expose private conflict titles in a group response.

## Attire applicability

Import `dress_applicability` as `required`, `not_applicable`, or `unknown` from
verified owner/calendar context. Do not infer it from a title. Omitted values
preserve the legacy unknown behavior. An explicitly not-applicable meeting can
send an otherwise complete authorized reminder without a dress rule. Conflicting
attire text must be reconciled before importing a not-applicable event.

## Mixed-role reminders

For an event marked `mixed_role_audience: true`, record verified event-audience
roles in the standing policy's `recipient_roles` mapping (address to role). Every
authorized recipient needs an applicable role. The planner creates separate
role-labelled messages with distinct cadence/group IDs and volunteer-safe dress
sources, and each claim reconstructs its current group. Missing/private/conflicting
requirements remain blocked for that group. A sent recipient cannot receive the
same cadence again merely by changing their role group; use explicit corrections.
The mapping is supplied verified context, not a role inferred from a name or email.
