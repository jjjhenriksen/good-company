# Roadmap: a coordinator’s assistant across nonprofits

The engine and instructions are a foundation, not a verified live service.
PRs 1–5 are merged: outbound source privacy, task-policy enforcement, delivery
history, packaging/CI and the initial audit documentation. The skills now separate
operations, events, volunteers and knowledge; [ADAPTING.md](ADAPTING.md) describes
the intended organizational range. Items below are **not implemented** unless
explicitly marked as existing. Priority reflects dependency and observed gaps,
not a promised release date.

Implementation is tracked in [56 atomic roadmap issues](https://github.com/jjjhenriksen/good-company/issues?q=is%3Aissue%20label%3Aroadmap):
10 P0, 15 P1 and 31 P2. Each issue has a type, area, acceptance criteria and
dependency links where applicable. Optional modules are discovery work.

## P0 — Prove an installable, autonomous pilot

1. **Real runtime and provider receipts.** [#7](https://github.com/jjjhenriksen/good-company/issues/7), [#8](https://github.com/jjjhenriksen/good-company/issues/8), [#9](https://github.com/jjjhenriksen/good-company/issues/9). Boot the exact release image on an
   available Plow line. Verify volume ownership, a real model reply, calendar and
   mail accounts, tool permissions and state after restart. Configure one test
   address and one scheduler job in the owner context. Import a complete scoped
   calendar, allocate a task, send an authorized reminder and task notice, and
   repeat without duplicates. Exercise pause, cancellation, changed sources,
   verified decline/completion and ambiguous delivery. A provider requiring
   per-send approval does not satisfy unattended operation.
   **Done:** record commit, image digest, job execution and genuine provider
   receipts, without secrets. Pass [ACCEPTANCE.md](ACCEPTANCE.md); a build or saved
   schedule is insufficient.
2. **Conversational onboarding and readiness.** [#10](https://github.com/jjjhenriksen/good-company/issues/10), [#11](https://github.com/jjjhenriksen/good-company/issues/11). Turn setup into a short sequence
   that previews one useful result, confirms the standing remit and explains
   unavailable connections. Show actual source freshness, last complete calendar
   refresh, pending exceptions, last scheduler run and delivery state. No
   additional per-message gate for work already covered by standing authority.
   **Done:** a fresh owner configures a fictional organization without editing
   JSON; persisted settings match their instructions and missing connections
   cannot appear ready. Depends on real runtime capability discovery.
3. **Submission receipts.** [#12](https://github.com/jjjhenriksen/good-company/issues/12), [#13](https://github.com/jjjhenriksen/good-company/issues/13), [#14](https://github.com/jjjhenriksen/good-company/issues/14), [#15](https://github.com/jjjhenriksen/good-company/issues/15), [#16](https://github.com/jjjhenriksen/good-company/issues/16). Pass checks on the exact release commit; deliberately
   publish MIT source and a public image; record a working video and actual-agent
   image with fictional data; verify slug ownership and genuine accepted usage;
   register media/install links and obtain organizer verification and initial
   one-click admission. **Done:** a new user completes the published installation
   and the Index shows the required listing/media/usage/verification. Follow
   [RELEASE.md](RELEASE.md). No live pilot or publication receipt exists yet.

## P1 — Remove barriers to broader nonprofit adoption

| Feature | Audit evidence / why it matters | Done when |
|---|---|---|
| Separate event category from dress applicability — [#17](https://github.com/jjjhenriksen/good-company/issues/17) | `core.py::_autonomous_scope` needs an event type, while `_draft` runs dress resolution for every typed event. Ordinary online meetings therefore get blocked. | Authorized categories work with explicit dress applicability: required, not applicable, or unknown. A no-attire meeting sends under remit; required/unknown attire never bypasses missing-source checks. Existing privacy/conflict cases still pass. |
| Per-event and program audiences — [#18](https://github.com/jjjhenriksen/good-company/issues/18), [#19](https://github.com/jjjhenriksen/good-company/issues/19) | `configure_autonomy` supplies one global reminder recipient list; each event has one dress role. Different teams or programs cannot safely share that delivery model. | Each event resolves a verified audience within standing authority. Mixed-role content stays appropriate for each recipient; moving programs or removing consent invalidates old queues. Test two programs with no recipient or source leakage. |
| Consent, preferences and one communication budget — [#20](https://github.com/jjjhenriksen/good-company/issues/20), [#21](https://github.com/jjjhenriksen/good-company/issues/21), [#22](https://github.com/jjjhenriksen/good-company/issues/22) | Event daily limit exists; task notices have no global daily limit. Quiet hours are fixed and there is no unified unsubscribe/preferences workflow. | Verified stop requests suppress future claims across event/task queues; per-channel preferences, local quiet hours and a shared budget persist. Digesting cannot hide urgent authorized corrections. Test queued notices and concurrent claims after revocation. |
| Explicit eligibility requirements — [#23](https://github.com/jjjhenriksen/good-company/issues/23), [#24](https://github.com/jjjhenriksen/good-company/issues/24) | `tasks.py::_eligible` accepts any intersecting role; skill minimums, opt-in and availability are checked, but training expiry and combined-role requirements are absent. | Tasks distinguish ANY/ALL role requirements and verified, dated credentials. Expired/unknown requirements block allocation. Organizational requirements are supplied facts, not inferred from age, identity or nonprofit type. |
| Changes, corrections and task/event linkage — [#25](https://github.com/jjjhenriksen/good-company/issues/25), [#26](https://github.com/jjjhenriksen/good-company/issues/26), [#27](https://github.com/jjjhenriksen/good-company/issues/27) | Event changes invalidate reminders, but tasks have independent immutable time windows. Already attempted messages require manual provider reconciliation; overdue notices can retain old sender/recipient data. | An event move/cancellation produces a traceable task impact plan and authorized correction workflow. No silent reassignment, stale-address send or duplicate after uncertainty. Test changes before and after delivery and provider failure mid-correction. |
| Reliable inbound replies and provider adapters — [#28](https://github.com/jjjhenriksen/good-company/issues/28), [#29](https://github.com/jjjhenriksen/good-company/issues/29), [#30](https://github.com/jjjhenriksen/good-company/issues/30), [#31](https://github.com/jjjhenriksen/good-company/issues/31) | Identity checking, calendar normalization and mail sends are currently agent instructions using inherited tools. No tested adapter contract enforces them. | Connectors expose verified account/sender IDs, complete paginated recurring-event reads, stable receipts and explicit permission/error states. Spoofed declines do not mutate tasks; retries reconcile provider state. Prove Google path first, then another provider without changing domain logic. |

Event/audience/consent changes require schema migration and compatibility checks;
don’t solve them by clearing blockers or relabeling unknown facts as verified.
Provider-level idempotency should be used when actually supported, with documented
fallback reconciliation where unavailable.

## P2 — Knowledge that remains useful and trustworthy

- **Source lifecycle and precedence.** [#32](https://github.com/jjjhenriksen/good-company/issues/32), [#33](https://github.com/jjjhenriksen/good-company/issues/33), [#34](https://github.com/jjjhenriksen/good-company/issues/34). Existing ingestion replaces one source and
  marks general knowledge stale after a fixed 180 days. Dress rules have richer
  date/review metadata; general documents lack withdrawal, effective-date and
  authority resolution workflows. Add explicit retirement, version/provenance,
  review dates, conflict handling and organization-supplied precedence.
  **Done:** a withdrawn policy cannot answer a new question or authorize a queued
  message; conflicting/expired material yields an actionable evidence gap.
- **Retrieval and answer evaluation.** [#35](https://github.com/jjjhenriksen/good-company/issues/35), [#36](https://github.com/jjjhenriksen/good-company/issues/36). Existing search is lexical FTS5/BM25;
  OpenClaw interprets the hits. Build a cited-question set across at least three
  fictional nonprofit types, including paraphrases, absent answers, conflicting
  rules, private/public material, tables and scanned documents. Evaluate extraction
  and answer grounding before deciding whether hybrid/semantic retrieval helps.
  **Done:** publish measured retrieval and citation accuracy with failures; no
  private source contents appear in volunteer answers or messages.
- **Authenticated participant access.** [#37](https://github.com/jjjhenriksen/good-company/issues/37). Audience labels are filters, not access
  control. The current image exposes trusted-operator tools and shared files.
  Separate participant Q&A from privileged configuration/delegation tools before
  opening a public or member-facing channel. **Done:** authenticated roles and
  tool restrictions enforce access even when prompts/documents request otherwise;
  cross-role and cross-organization adversarial checks pass.
- **Language and accessibility.** [#38](https://github.com/jjjhenriksen/good-company/issues/38), [#39](https://github.com/jjjhenriksen/good-company/issues/39). Current profile supports greetings/signoffs;
  broader organization terminology, locale, preferred language and communication
  accessibility are not structured settings. **Done:** participants can choose
  supported formats/languages; translated rules preserve conditions and cite the
  original; timezone/daylight-saving tests cover a distributed team. Avoid
  mandatory titles, family structures or English-only ceremonial vocabulary.

## P2 — Volunteer follow-through and coordinator workload

- **Shifts and staffing.** [#40](https://github.com/jjjhenriksen/good-company/issues/40), [#41](https://github.com/jjjhenriksen/good-company/issues/41). Add multi-person shifts, open slots, signup/waitlists,
  verified RSVP responses and replacement offers with explicit capacity.
  **Done:** two simultaneous signups cannot overbook; declines reopen only the
  correct slot; authoritative staffing constraints survive reallocation. Depends
  on eligibility and identity work above.
- **Overdue work and fair allocation.** [#42](https://github.com/jjjhenriksen/good-company/issues/42), [#43](https://github.com/jjjhenriksen/good-company/issues/43). Past open assignments still consume
  capacity; delegation skips tasks already started. Add explicit overdue and
  follow-up outcomes, explanations of selection and measured workload fairness.
  **Done:** a stale task is surfaced without being silently completed; skill,
  availability and consent constraints remain stronger than ranking preferences.
  No inferred “reliability” or private weakness labels.
- **Program outcomes.** [#44](https://github.com/jjjhenriksen/good-company/issues/44), [#45](https://github.com/jjjhenriksen/good-company/issues/45). Add verified attendance, volunteer hours and a concise
  weekly operating brief/export. **Done:** figures come from confirmed records,
  can be corrected and do not turn queued messages into claimed participation.
- **Optional modules after the core works.** [#46](https://github.com/jjjhenriksen/good-company/issues/46), [#47](https://github.com/jjjhenriksen/good-company/issues/47), [#48](https://github.com/jjjhenriksen/good-company/issues/48), [#49](https://github.com/jjjhenriksen/good-company/issues/49). Consider resource/equipment booking,
  accessibility requests, form checklists and donor/beneficiary integrations only
  with a concrete organization’s requirements. These need separate access and
  retention decisions; they are not universal onboarding requirements. No payment,
  safeguarding certification or case-management capability is implied today.

## P2 — Operability and maintenance

- [#50](https://github.com/jjjhenriksen/good-company/issues/50). Validate nested CLI shapes and bounded input sizes with structured errors;
  malformed user input must not expose tracebacks or mutate partial records.
- [#51](https://github.com/jjjhenriksen/good-company/issues/51). Restrict development proxy Host values and test the pinned Caddy configuration.
- [#52](https://github.com/jjjhenriksen/good-company/issues/52), [#53](https://github.com/jjjhenriksen/good-company/issues/53), [#54](https://github.com/jjjhenriksen/good-company/issues/54). Add private backup/restore, data export/deletion/retention, schema migration and
  rollback checks. **Done:** recover a fixture database with unchanged delivery
  history and install identity; restarting never replays accepted sends.
- [#55](https://github.com/jjjhenriksen/good-company/issues/55). Add health reporting for stale calendars, paused policy, unavailable providers,
  missing credentials and stalled claims. Reports must omit secrets and recipient
  lists; unresolved failures remain distinguishable from quiet successful runs.
- [#56](https://github.com/jjjhenriksen/good-company/issues/56), [#57](https://github.com/jjjhenriksen/good-company/issues/57). Review/pin CI dependencies, base/runtime compatibility and upgrade behavior.
  Keep packaged-skill/example checks and installed-wheel tests. A skills rename
  must not leave duplicate operational jobs or erase persistent state.

## Adoption acceptance matrix

Before describing the product as broadly deployable, run these with fictional
sources and an explicitly authorized test mailbox:

| Organization scenario | Required demonstration | Dependencies |
|---|---|---|
| Food bank packing shift — [#58](https://github.com/jjjhenriksen/good-company/issues/58) | Only eligible opted-in volunteers get assignments; declined work gets a qualified replacement | Eligibility, staffing, verified replies |
| Arts nonprofit rehearsal — [#59](https://github.com/jjjhenriksen/good-company/issues/59) | Distinct teams receive the correct event change and task follow-up | Program audiences, task/event linkage, corrections |
| Mutual aid team — [#60](https://github.com/jjjhenriksen/good-company/issues/60) | A helper’s stop request prevents every later notice while other work continues | Unified consent, shared budget, identity |
| Nonprofit board online meeting — [#61](https://github.com/jjjhenriksen/good-company/issues/61) | Routine reminder works without manufacturing a dress policy; private availability stays private | Optional dress applicability, scoped calendars |
| Youth organization event — [#62](https://github.com/jjjhenriksen/good-company/issues/62) | Role/date-specific attire cites current supplied rules; private sources stay private | Source lifecycle, existing dress/privacy checks; authenticated access before member-facing use |

These are proposed acceptance scenarios, not evidence of completed deployments.
