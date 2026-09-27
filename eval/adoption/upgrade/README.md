# Upgrade acceptance — #57

Status: local preflight passed; live acceptance remains pending.

Run `python3 eval/adoption/upgrade/preflight.py` from a checkout with Python 3.11 or later.
The checked-in result identifies the tested base commit. These are existing
fictional contract fixtures, not a deployed organization or provider simulation
presented as real delivery. The runner never accesses a mailbox or sends messages.

## Live completion procedure

Upgrade an existing supported image with a nonempty state volume. Record before/after image digest, install identity, inherited/custom skill inventory, remit and receipt counts. Verify exactly one operational job and no duplicate provider send after its next real run.

Before live sends, connect Latch and the provider, verify account identity/scopes,
and obtain explicit authorization for the exact test mailbox. Keep real addresses,
tokens and private message content out of this repository. Record release image,
actual job/operation IDs, genuine provider acceptance, received-message observation,
and repeat-run send counts separately. A unit-test receipt is not provider proof.

Live baseline on 2026-09-26: Latch setup and Google connection completed. Four
authorized owner-loopback emails were accepted and observed; reminder/task repeat
claims were refused, and STOP cancelled two queued notices. See the board and
mutual-aid live results. This scenario still needs its own outstanding acceptance
evidence. Merging this preflight does not complete the linked issue.

## Actual local upgrade observation

On 2026-09-26, upgraded the running ARM64 preview from image
`sha256:10918def35c76de196ced2be90a3dce8e0d830e774ff106fcf13692557cea7c3`
to merged commit `29772d7` and image
`sha256:c8934bd9150844eedef6fb880c6dcdfeec65dbf681f8fc7997ed4a318a41d2cb`.
The existing coordination database was backed up before replacing the container;
the existing named volumes were retained. First coordination access migrated
schema version 0 to 1. SQLite integrity passed, every pre-existing setting retained
its value, and all inherited/custom skill directories remained present. The health
check added its own `health:last` observation; this is an expected state change.

After the gateway reported ready, a genuine GLM-5.2 model turn used the installed
CLI and returned the saved fictional organization profile and correct unresolved
readiness gaps. An initial call during startup was refused before a session was
created; it was retried only after checking that absence and gateway readiness.

Limitations: the original reminder ledger was empty, so equality across upgrade
is not proof of preserving real sent receipts. There is still no operational Good
Company scheduler job, registered Index install identity or next-run delivery
proof. This is a real source-image upgrade with retained local state, not a claim
that all base-image, identity, skill-loading and scheduled-delivery criteria pass.

## Current-code upgrade with nonempty receipt history

A second local upgrade deployed merged source `7ea8c8997526a48e6efac387e4e5226586950585`
on September 26, 2026 (Los Angeles). [runtime-result.json](runtime-result.json)
records the immutable old/new images, genuine model run and verification scope.
Both existing databases were backed up before container replacement, retaining the
same named volumes. Every table's row hash matched before replacement, after boot,
and after the model check. The isolated self-test database contains one reminder,
three task notices, one assignment and the recorded opt-out; this now covers
preservation of existing real self-test receipt history, unlike the earlier empty
main ledger check. Both databases retained SQLite integrity and disabled autonomy.

All 27 installed Python modules matched the committed sources. The real GLM 5.2
trajectory contains exactly three successful local commands: the cycle command's
help without inherited PYTHONPATH, profile, and autonomy. The model read the saved
fictional club and Los Angeles timezone; autonomy remained null in the main DB.
The dashboard returned HTTP 200. Three existing background job IDs, enabled states
and schedules were preserved; none is a Good Company operational delivery job.

This verifies an actual application-code upgrade and retained state. It does not
complete #57's exactly-one-operational-job or next-run delivery criteria. The base
runtime version was not changed, no provider was contacted by the verification
commands, and raw databases/trajectories remain private.
