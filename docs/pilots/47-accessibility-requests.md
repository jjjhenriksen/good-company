# Accessibility requests: optional pilot proposal

Refs #47. Decision: **conditional scope; disabled until intake and owner are named**.

Bethel 337 provides a concrete organization context for an event pilot. No actual
accessibility request, requester, intake channel or fulfillment owner has been
supplied. Do not infer individual needs from membership or philanthropic activity.
Existing message-format preferences do not prove service arrangements.

## Proposed event workflow

For one owner-selected event, a requester describes an arrangement they want,
such as an accessible route or a captioned presentation. They choose who may see
the request and may withdraw it. A named event coordinator acknowledges it,
contacts the authorized venue/service owner, and records a result with an opaque
evidence reference. This is a proposal for local testing, not an assertion that
Bethel 337 currently uses this process.

| Status | Required evidence | Message permitted |
| --- | --- | --- |
| requested | Requester's consent and event ID | Request received |
| acknowledged | Named coordinator accepts responsibility | Coordinator reviewing |
| arranged | Responsible service owner confirms the arrangement | Arrangement confirmed, with limitations |
| verified | Coordinator checks the actual arrangement | Arrangement checked |
| unavailable | Owner confirms inability and requester receives options | Requested arrangement unavailable |
| withdrawn | Requester withdraws consent | Request withdrawn |

A sent message cannot change a request to arranged or verified. A moved or
cancelled event invalidates verification tied to the previous location or time.
Recheck arrangements before confirming the replacement event.

## Minimal data and access

Store request ID, event ID, participant ID, requested arrangement, visibility consent,
responsible owner ID, status, expiry and an opaque confirmation reference.
Do not request diagnoses, medical history or proof of disability. Restrict free text
to the arrangement and review it before sharing. Keep identity outside group notices.
Only the requester and explicitly authorized coordinator/service owner can view it.
Withdrawal stops future coordination; keep a minimal audit status without the
request text only if the owner has defined a necessary retention policy.

Choose an actual deletion date at intake, tied to the event and follow-up period.
A default indefinite retention policy is unacceptable. Reminder authority must be
explicit for this workflow; general volunteer permission does not authorize disclosure.

## Local acceptance plan and enabling requirements

A fictional requester asks for captions. A fictional coordinator acknowledges it;
a provider confirms availability; verification records the actual service check.
The harness must show that acknowledgment and delivery never assert fulfillment,
event changes require re-verification, withdrawal removes queued follow-up, and a
second team cannot see the request.

Before creating implementation issues, supply the actual intake channel, coordinator,
service authority, consent wording and retention duration. Existing [JDI resources](
https://jobsdaughtersinternational.org/resources/) provide organizational context,
but do not establish this local workflow. An official form title alone is not evidence
of an accessibility intake requirement.
