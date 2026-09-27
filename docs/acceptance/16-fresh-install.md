# Fresh-user installation acceptance (#16)

Status: incomplete. One-click acceptance awaits #15's organizer admission;
manual installation can be checked independently. The maintainer's private local
ARM64 preview is evidence for #7, not a clean-user published install result.

## Guide corrections found during the clean-install audit

On September 26, 2026, the documented empty `plow-credentials` preflight
placeholder reproduced an installation failure with the official Plow CLI
(`3033a59754067bb21b4b6b2844967db343ecf7bd`): `mint` refuses every existing
credential file before contacting the service, including an empty placeholder.
The same refusal occurs in `deploy --local`, which calls `mint` first.

Compose now accepts a command-scoped `PLOW_CREDENTIAL_FILE=/dev/null` override
for builds and compatibility checks. Both platform configurations validate in a
directory with no credential file; normal configuration still refuses a missing
credential file. CI checks all three conditions without manufacturing one.
The documented native build and preflight command also passed in a separate
Compose project with fresh volumes (`Linux aarch64`, `ready: true`); its scope
is filesystem syscall support only.

The Mac's system Python 3.9 also reproduced `ModuleNotFoundError: tomllib` when
invoking the CLI. Activating a fresh Python 3.13 virtual environment made the
CLI's existing `python3` launcher work. INSTALL.md now documents this setup and
separate AMD64/native ARM64 startup commands, avoiding a second mint or accidental
return to AMD64 after the native preflight.

These corrections do not establish fresh account activation, a model reply,
durable state or one-click acceptance. No line was allocated and no message sent
by this guide audit. The checklist remains incomplete.

## Remaining acceptance run

Start in a clean directory/account session using only the published INSTALL.md.
Record OS/architecture and exact source commit/public image digest. Follow one-click
and manual paths only as documented; do not inject maintainer-only files or patch
commands silently. For Apple Silicon use the documented native override. For an
existing install, test migration separately; never erase its volumes for a clean run.

Observe authentication, gateway ready, a real model reply, installed skills/tools,
profile persistence after restart and sending disabled until verified setup. Check
the public image can be obtained without maintainer registry credentials. Record
any guide corrections as a patch and repeat the failed step from a fresh state.
Finish with preserved install identity and a receipt-backed pass/fail table. Do not
check the release checklist on the strength of a container build or fixture alone.
