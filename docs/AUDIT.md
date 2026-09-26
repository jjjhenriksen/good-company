# Engineering audit — 2026-09-25

Baseline: `cd0efe4`, the initial committed snapshot. All 36 original files were
reviewed, including code, tests, examples, prompts, deployment files and docs.
The baseline passed 51 unique behavior tests. Static review included an
independent security baseline and architecture review. A passing suite did not
establish deployment or autonomous-provider behavior.

The initial history groups the existing snapshot by feature; it does not purport
to recover the original edit chronology. Calendar, rules, autonomy and task
commits were each tested from their exact staged tree (19, 34, 40 and 51 tests).

## Confirmed problems and fixes

| Finding | Impact | Work |
|---|---|---|
| Private dress rules used in outgoing templates | Coordinator-only text/citations could enter volunteer mail. Reproduced locally with fictional content. | [PR 1](https://github.com/jjjhenriksen/good-company/pull/1): volunteer-safe composition, claim-time template check and legacy-template refresh. |
| Task cadence revocation and stale policy reads | Removed offsets remained sendable; an owner pause could race a claim or allocation. | [PR 2](https://github.com/jjjhenriksen/good-company/pull/2): transactional policy reads, cadence reconciliation and claim guard. |
| Delivery history keyed only to event revision | Changing an already-attempted event could queue another send, including after an uncertain result. | [PR 3](https://github.com/jjjhenriksen/good-company/pull/3): cross-revision delivery history and explicit correction exceptions. |
| Empty calendar snapshots had no sync watermark | An older snapshot could repopulate a freshly empty scope. | PR 3: persisted calendar-level watermark. |
| No automatic PR checks or installed-package test | Source tests could pass while the distributable failed. Declared build dependency floor predates its license format. | [PR 4](https://github.com/jjjhenriksen/good-company/pull/4): supported-Python CI, wheel installation smoke test and corrected build floor. |
| CLI operational errors could escape its JSON contract | Corrupt databases emitted a traceback instead of a structured failure. | PR 4: database errors, object validation and connection cleanup. |
| Build context used only a denylist | Unexpectedly named local documents could enter the Docker build context. | PR 4: runtime-source allowlist and broader local-secret ignores. |

PRs 1–5 were reviewed and merged into `main` at `a7a83db`. Their individual
validation results remain in the PR descriptions. The file inventory below
preserves the original baseline paths; current skill names and portability
findings are in [ADAPTING.md](ADAPTING.md) and [ROADMAP.md](ROADMAP.md).

The security scan classified the private-rule leak as a medium-severity disclosure.
The task lifecycle defects are separately tracked as engineering correctness
failures under the documented trusted-operator model. No public unauthenticated
API was inferred. No actual email or private pilot document was used in testing.

## Combined validation

The five PRs were first combined without conflicts on `audit/integration-check`.
At commit `3254ee9a5cbef1a72bec8b0f77858d25f4b20682`:

- 70 unique tests passed locally on Python 3.12.
- [GitHub CI](https://github.com/jjjhenriksen/good-company/actions/runs/36217186171)
  passed on Python 3.11, 3.12 and 3.13, including both demos, wheel installation
  outside the checkout and Compose validation.
- [Linux/amd64 image build and container smoke test](https://github.com/jjjhenriksen/good-company/actions/runs/36217167986)
  passed. The smoke test exercised the installed CLI and SQLite engine with
  networking disabled and the service entrypoint overridden.
- Source credential-pattern checks found no matches; no live pilot inputs were
  included. This is a scoped check, not a guarantee about arbitrary future files.

No public image was pushed. No full Plow gateway boot, real model conversation,
mail send, live calendar synchronization or Index registration was tested.
The merged `main` tree at `a7a83db` matches the final integration branch exactly.
These checks establish packaged-engine behavior, not a live-service release.

GitHub reported deprecation advisories for the Actions' Node 20 declarations
(running under Node 24) and upcoming runner-image migration. The runs succeeded;
actions/runtime updates remain maintenance work. Security-scan token usage was
not available from the tool result.

## Complete baseline file inventory

| File | Review result / remaining boundary |
|---|---|
| `.gitignore` | Excludes known state/credentials; broader secret patterns in PR 4. |
| `.dockerignore` | Replaced by an allowlist in PR 4. |
| `.github/workflows/build-image.yml` | Manual build only; no runtime proof. PR 4 adds packaged-engine smoke test. Actions use major-version tags. |
| `Dockerfile` | Pinned base, non-root final user, persistent DB path; inherited boot/auth not inspected inside image. |
| `compose.yml` | Loopback dashboard, state volume, blank preview listing ID; needs actual boot. |
| `dev/Caddyfile` | Removes forwarded identity and rejects foreign Origin. Arbitrary Host and absent Origin still accepted; Host allowlist is follow-up hardening. |
| `pyproject.toml` | No runtime dependencies; Python floor declared; build floor corrected in PR 4. |
| `LICENSE` | Original project is MIT; inherited components retain separate licenses. |
| `good_company/__init__.py` | Package marker; no executable side effects. |
| `good_company/cli.py` | Allowlisted trusted commands; no identity boundary. Error contract improved in PR 4. Nested payload validation remains uneven. |
| `good_company/core.py` | Bound SQL, source filters, event revisions and serialized claims; concrete fixes in PRs 1 and 3. |
| `good_company/tasks.py` | Deterministic eligibility/capacity allocator; policy lifecycle fixes in PR 2. No global optimization or provider adapter. |
| `tests/test_core.py` | 19 baseline cases; sequential two-worker test, not broad concurrency proof. |
| `tests/test_dress_code.py` | 15 cases; direct privacy covered, outbound privacy missing until PR 1. |
| `tests/test_autonomy.py` | 6 cases; standing scope, pause and daily event limit. |
| `tests/test_tasks.py` | 11 cases; allocation/declines/notices. Revocation races and removed cadence missing until PR 2. |
| `scripts/good-company` | Shell wrapper preserves arguments; no string interpolation. |
| `scripts/demo.py` | Fictional temporary DB; calendar dates depend on current clock. |
| `scripts/autonomous_demo.py` | Fictional deterministic replay; no real sends or synthetic live receipts. |
| `examples/profile.json` | Fictional organization and local-time cadence. |
| `examples/handbook.md` | Fictional cited material, explicitly not JDI policy. |
| `examples/dress-code.json` | Fictional role-specific rules with validity/review dates. |
| `examples/autonomy.json` | Non-deliverable addresses, exact scopes, event-only daily limit. |
| `examples/team.json` | Fictional opted-in roster, skills and explicit availability. |
| `examples/tasks.json` | Fictional immutable tasks with role/skill requirements. |
| `prompt/AGENTS.md` | Trusted Guardian assistant; authority and privacy guidance. Prompt instructions are not access control. |
| `skills/community-coordinator/SKILL.md` | Honest claim/receipt and complete-import contracts. Provider reads/sends/scheduler are instructions, not tested adapters. |
| `skills/guardian-support/SKILL.md` | Cited dress resolution; no inferred regulatory hierarchy. Outbound audience behavior corrected in PR 1. |
| `skills/autonomous-guardian/SKILL.md` | Standing-policy routine operations; inbound identity verification still external. |
| `README.md` | Product intent and implemented limits; opening wording clarified to avoid implying proven unattended operation. |
| `INSTALL.md` | Connection/scheduler setup requires live proof; repository acquisition step added. |
| `docs/ACCEPTANCE.md` | Real model/provider scenarios defined but not executed. |
| `docs/RELEASE.md` | Tracks distinct publication receipts; repository existence is separate from public visibility. |
| `docs/VOICE.md` | Friendly bounded voice; obsolete claim that roster tools do not exist corrected. |
| `docs/DEMO-OUTPUT.txt` | Captured fictional example, not a fresh live-service receipt. |
| `docs/AUTONOMOUS-DEMO.txt` | Captured deterministic queue replay, explicitly not delivery. |

## Remaining product and release gaps

See [ROADMAP.md](ROADMAP.md) for the exact acceptance criteria. The critical path
is a connected, authenticated model run that imports the correct calendar scope,
answers from supplied sources, allocates work, sends to one authorized test
recipient on schedule, and proves no duplicate on the next run.

Other limits remain explicit: one event audience per installation, lexical rather
than semantic/vector retrieval, no raw ICS recurrence parser, no general JDI
compliance engine, no roster certification verification, no RSVP/form intake, no
provider-level idempotency, no encrypted-at-rest DB, no hostile-member isolation,
and no global task-message budget. These are not all required for a small private
pilot, but must not be advertised as implemented.

Review does not prove absence of all bugs. The inherited runtime and real provider
permissions, scheduler execution, source extraction quality, prompt-injection
behavior, receipts, public image availability and Index acceptance need their own
verification. No audit of a configured live organization has been performed.
