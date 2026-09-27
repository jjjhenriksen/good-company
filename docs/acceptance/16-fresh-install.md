# Fresh-user installation acceptance (#16)

Status: incomplete. [Organizer admission](15-index-admission.md) was observed on
September 27 at 14:04 UTC; the listing now exposes its texting installation link.
A fresh one-click installation has not been performed.
The separate source installation below verifies native startup, a real model reply
and persistent paused setup using an already authenticated account. It does not
establish a new phone-login session or texting/one-click acceptance.

## Isolated manual source installation — September 27, 2026 UTC

Public clones of Good Company `3caa803bd2d4b7f59d2ab798614e64aff228d068` and the
official Plow CLI `3033a59754067bb21b4b6b2844967db343ecf7bd` were used in a new
private directory. Python 3.13.13 ran in a fresh virtual environment. The updated
guide's separate project and loopback port 3017 avoided the existing installation.
Both target state volumes and the credential file were absent before the run.
The previously authenticated owner's Plow account was reused; no account token or
existing agent credential was copied into the new checkout or image.

| Check | Observed result |
| --- | --- |
| Fictional local demo and native preflight | Passed; Linux aarch64 syscall check reported ready. |
| Fresh credential and volumes | A previously free line received a newly minted mode-0600 credential. Two separate named volumes were created. |
| Native image | `sha256:5db06f3f29dac4cd6ff35e3a9507c35c950ca47df8ac32f5a8f898ea9fd0d09d`, built from the public source clone. |
| Owner dashboard | HTTP 200 and authenticated local `dev-owner` session on port 3017. |
| Genuine model response | The GLM 5.2 dashboard session returned `GOOD_COMPANY_FRESH_INSTALL_OK` at 06:28 UTC; channel delivery was not requested. |
| Installed capabilities | All four Good Company skill files and the coordination command were present. |
| Conversational setup | The model saved Fictional Fresh Install Check with the requested profile and `enabled: false` remit. Direct database comparison confirmed every supplied field. |
| Outbound state | Zero scheduled jobs, connection attestations, calendar events or queued notices. Only reserved `example.invalid` addresses were configured. |
| Initial restart | Saved settings and credential survived, but the proxy retained the old network namespace and the dashboard stopped responding. Tracked in #168. |
| Restart with dependency fix | The proxy restarted after the agent, both shared the live namespace, HTTP 200 returned, and the conversation reloaded. Exact settings and credential comparisons passed; sending remained paused and queues empty. |
| Existing installation | Its container identity, image and start time were unchanged. Its credentials and volumes were not reused. |

The direct gateway CLI attempt returned `unauthorized`; the documented local owner
dashboard supplied the intended authentication context and produced the actual
response. No authentication policy was relaxed. The model's setup used local
commands only; two exploratory empty-input schema probes failed harmlessly before
the successful onboarding command. No Google connection, real recipient message,
schedule or verified connection attestation was created.

The restart fix uses explicit dependency restart propagation. Its credential-free
pinned-Caddy regression fails against the old configuration and passes both a
whole-project restart and a targeted agent restart with the correction. Package
checks and this native source run are not a fresh public AMD64 image boot, new
phone activation, SMS receipt or completed one-click installation. Those remain
unverified; the later admission evidence is recorded separately in #15.

## Updated isolated installation — September 27, 2026, 07:12 UTC

The same isolated source checkout was fast-forwarded to published main
`80f10900bfb1cd5c3a46bb306e6b165debbc457f`, then rebuilt and started with the
documented native Compose override, separate project and loopback port. This is
an update of the fresh installation above, not another fresh account activation.

- Native image: `sha256:615ae26640c3d2775994dc20c5b81b6669f0e20cf1edb618eab34f450faa8ce9`.
- All 29 installed coordination modules matched the source files byte for byte.
- The existing owner conversation reloaded, and GLM 5.2 returned the actual new
  response `GOOD_COMPANY_UPDATED_INSTALL_OK` at 07:12:15 UTC. No tools or external
  channel deliveries were requested or shown for that response.
- A subsequent documented `restart agent` restarted the dependent proxy too.
  HTTP 200 and matching network namespaces returned; both model replies and the
  original setup conversation remained visible after browser reload.
- Exact profile/remit and credential comparisons passed before and after restart.
  Sending stayed paused, with zero jobs, connection attestations, events or notices.
- The original separate installation retained its container identity, image and
  start time. Only the isolated test project was updated, then stopped; its
  credential and volumes were retained.

The [build-only AMD64 run](https://github.com/jjjhenriksen/good-company/actions/runs/36302320179)
for this exact source passed 450 tests, the real Docker context canary check, image
construction and installed-package checks. Registry login and publication were
skipped. The existing public release was not replaced, and the remaining phone,
public AMD64 runtime and one-click acceptance boundaries above still apply.

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

## Fresh hosted public-image deployment — September 27, 2026

The official Plow CLI requested a new hosted agent on a previously free line,
using the existing owner account and the exact public AMD64 image below. Existing
local installations, credentials and volumes were not modified.

- Source: `5fa457253781a5d95680d2e7a9bda31d0128b6f5`.
- Image: `ghcr.io/jjjhenriksen/good-company@sha256:438548cc74a5fcc79323c4d1b20cffe6780220e8b4576b1a7dcd6d615c524ce8`.
- [Build and publication run](https://github.com/jjjhenriksen/good-company/actions/runs/36332812906)
  completed successfully. All 479 installed-image tests and both fictional demos
  passed before publication, along with the package and build-context gates.
- Anonymous registry access returned the manifest and configuration. The manifest
  bytes matched the registry digest; configuration identified Linux AMD64.
- Plow transitioned from `provisioning` to `running`, with no reported failure code
  and the requested image digest unchanged.
- The supplied host initially lacked DNS, then resolved. Browser navigation reached
  the hosting provider's authentication page. That page is not an authenticated
  Good Company dashboard or proof of a model response.
- The normal Plow owner controls could not be inspected further because the Mac
  locked. No alternate login, security relaxation, setup SMS or email was used.
- Plow subsequently accepted promotion of this digest for new installations and
  the official CLI reported that the Index accepted its image update. The public
  listing response does not expose an image field, so that mirror was not
  independently readable there. The existing agents keep their
  images. [Preview release v0.1.1](https://github.com/jjjhenriksen/good-company/releases/tag/v0.1.1)
  records the same source and digest.

The separate hosted test remains available for continuation. A hosted model reply,
setup persistence, new phone/account activation and the actual Index texting flow
remain unverified. Issue #16 stays open; a host status is not full install acceptance.
