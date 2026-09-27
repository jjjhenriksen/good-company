# Fresh-user installation acceptance (#16)

Status: blocked by #15's admitted public release. The maintainer's private local
ARM64 preview is evidence for #7, not a clean-user published install result.

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
