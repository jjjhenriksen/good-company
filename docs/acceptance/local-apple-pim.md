# Local Apple PIM sandbox and remaining acceptance

This is a local preparation path for #16, #29, #31, #41 and #58–61. It is not a
replacement for the Plow deployment or completed live nonprofit acceptance.

## Create a separate macOS workspace

Use Python 3.11 or later and the already installed OpenClaw, Apple PIM plugin,
native CLI binaries and Node runtime, from the Good Company source checkout. This command neither installs them nor
copies an existing account's credentials. Choose a new private state directory
and an unused loopback port. Keep this directory outside cloud-synced storage.

```sh
python3 -m good_company.local_sandbox \
  --state /private/tmp/good-company-local-check \
  --plugin /path/to/apple-pim/openclaw \
  --launcher /path/to/openclaw/openclaw.mjs \
  --node /path/to/node \
  --bin-dir /path/to/apple-pim/binaries \
  --port 19843
/private/tmp/good-company-local-check/start.sh
```

An optional `--model ollama/<already-installed-model-id>` selects a local model
at loopback port 11434. The initializer checks the installed model reports tool
support before creating state. It does not download a model or reuse cloud credentials.
Without it, do not assume a model is configured or authenticated. Stop only this
foreground process to restart it; preserve its files and use `start.sh` again.
A temporary directory is disposable across system cleanup/reboot, so choose a
private durable directory when the sandbox must survive those events.

The initializer refuses an existing state directory. The new fictional ledger
is paused; calendars have an empty allowlist, mail/contacts/reminders are disabled,
and the gateway permits only calendar list reads. A generated local guard rejects
other calendar actions and per-call config/profile overrides before execution. It generates its own private
gateway token and never prints it. The gateway exposes the calendar's schema directly, binds to loopback, disables
cron and heartbeats, and starts with `OPENCLAW_SKIP_CHANNELS=1`. This supported runtime
flag preserves the plugin's tools while preventing its Apple Mail channel from
polling or answering mail. `channels.apple-mail.enabled=false` disabled the
entire plugin in the tested runtime and is unsuitable for a tools-only check.

Do not mark mail/calendar connections verified from a successful startup or
calendar list. A scope must be explicitly selected before event access. Do not
turn on mail or run live send tests without an authorized sender and test audience.

## Observed local run — October 1, 2026, America/Los_Angeles

Base source: `eaf99e2c111901a127a7ff067d950ae52ee1ff6d`, with this initializer.
The native runtime was OpenClaw 2026.9.7 (`e20a820`), Node 26.5.0, Darwin arm64.
The installed Apple PIM source and native binaries were reused without modification.

- `/healthz` and `/readyz` returned HTTP 200.
- The registered `apple_pim_calendar` tool returned a successful empty list under
  the new allowlist. The plugin's native helper handled Calendar read access;
  direct CLI authorization alone was write-only.
- The excluded `apple_pim_mail` tool returned HTTP 404. Explicit calendar create
  and config-directory escape attempts returned HTTP 403 from the local guard. No email was sent and no
  personal calendar event was imported or written.
- The paused profile/remit and gateway token hashes matched after a controlled
  stop and restart. Direct ledger reads found zero events and queued notices.
- The pre-existing Ollama Bonsai model rejected tool use. A separate local
  `qwen3:1.7b` model was obtained; its native capability report includes tools, and
  the gateway returned the genuine response `GOOD_COMPANY_LOCAL_OK`. The initializer
  now refuses a selected local model that lacks tool support. A model capability
  label alone does not prove that any requested tool was actually called.
- With the direct calendar schema, a subsequent model turn actually invoked
  `apple_pim_calendar` and returned the empty authorized list. The runtime
  terminal receipt names that successful tool. The earlier compact tool-search
  attempt emitted JSON as text and did not count as a call; direct schemas fixed
  this narrow local-model path.
- Startup explicitly skipped channels, cron and heartbeats. The existing gateway
  and Good Company installation were not restarted, configured or upgraded.

This establishes isolated native startup, helper/tool access, containment and
local ledger persistence. It does not establish a fresh phone/account activation,
Index installation flow, hosted restart persistence, a real provider receipt or
an authenticated participant reply. See [#16 evidence](16-fresh-install.md).

## Repeatable fictional scenario checks

```sh
python3 scripts/local_acceptance.py --report /private/tmp/good-company-cases.json
```

The runner groups existing domain regressions into four adoption scenarios and
fails if any selected test fails or disappears. It uses temporary fictional state,
reserved example addresses, simulated clocks and fixture providers. It does not
connect to Apple PIM or send messages. Its report explicitly sets
`live_provider_acceptance: false` and contains test IDs, counts and outcomes.

The October 1 run passed 19 checks: food-bank eligibility/capacity/replacement (5),
arts program separation/change/correction (5), mutual-aid stop/identity/budget (5),
and board reminders without dress rules/private conflict labels/deduplication (4).
These checks prepare #58–61; genuine receipt and identity requirements stay open.

The expanded runner adds six verified-reply checks (#29) and six signup-intake
checks (#41), for 31 grouped checks. Its `issues` map lists all twelve remaining
issues, their local coverage and exact missing evidence. A passing run still sets
`remaining_issue_acceptance: false`; it does not declare a simulated sender or
receipt genuine. Report files are created exclusively with mode 0600.

## Repeat the native startup and containment checks

From the source checkout, using the installed macOS runtime and a new directory:

```sh
python3 scripts/apple_pim_acceptance.py \
  --state /private/tmp/good-company-native-check \
  --plugin /path/to/apple-pim/openclaw \
  --launcher /path/to/openclaw/openclaw.mjs \
  --node /path/to/node \
  --bin-dir /path/to/apple-pim/binaries \
  --port 19846
```

This harness refuses existing state and occupied ports. It starts its own process
group, checks health/readiness, performs a genuine empty-allowlist calendar read,
and requires the runtime guard's precise denial for calendar writes and scope
overrides. The write probe names a deliberately nonexistent calendar, so it
cannot create a personal event if the guard regresses. Mail must be unavailable.
It then stops and restarts only its own process, repeats the tool checks and
independently compares the paused ledger's settings/counts and gateway token hash.
It stops the test runtime on completion and failure; the separately running local
instance and pre-existing installation remain available.

The resulting private `native-report.json` contains booleans and safe failure
classes, never credentials or native response bodies. `gateway-private.log` is
private diagnostic data and must not be uploaded as acceptance evidence. These
checks run through the native gateway, unlike the fixture checks. They establish
local startup/read access/containment/persistence, not a model turn, event sync,
participant identity, message delivery or fresh hosted installation. No model
credentials are required and the harness has no send option.

The October 1 automated native run passed all 12 checks against OpenClaw 2026.9.7
and the installed Apple PIM plugin, including both pre- and post-restart reads and
guard denials. The first run correctly failed its calendar-result assertion: the
plugin emits one JSON value after a datamarking preamble, with domain/action
metadata in `details`. The corrected parser accepts that exact content format,
rejects ambiguous/error/nonempty results, and passed the fresh second run. The
original local gateway remained healthy after the harness stopped its own runtime.

## Provider work that the probe exposed

| Requirement | Apple PIM evidence and next step |
| --- | --- |
| Complete scoped calendar (#31) | Native events accept an exact calendar ID and bounds, but use a result limit without total/truncation evidence. Read a sentinel beyond the allowed payload, validate returned range/scope, and refuse incomplete results before state replacement. |
| Stable recurring instances (#31) | The inspected event projection has eventIdentifier and recurrence rules, but no original occurrence timestamp. Establish stable expanded occurrence identities across moves/cancellations before treating it as a complete domain snapshot. Do not derive identity from the current start time. |
| Inbound identity (#29, #41) | `mail-cli auth-check` supports pinned trusted authserv IDs and operator-enrolled per-address expected DKIM signers. Only an independently established mailbox-level verdict can become VerifiedReply; ordinary From/SPF/domain pass is insufficient. Bind the selected mailbox and opaque evidence to the domain command, then run genuine and spoofed replies through that same path. |
| Mail receipts/reconciliation (#31, #58–61) | The inspected Mail.app send path returns AppleScript success and display text, without a provider operation/message receipt. Preserve an uncertain outcome until an exact-account reconciliation path establishes acceptance; never manufacture a receipt or resend an ambiguous attempt. |

Apple PIM is the owner's selected local integration candidate. No concrete external
pilot or production adapter is asserted by this probe. The calendar/mail provider
contract still needs the above implementation and same-path live evidence.
