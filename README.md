# Good Company

**An executive assistant for overworked nonprofit and community coordinators.**

Good Company is an OpenClaw agent that helps a community leader stop carrying
all the remembering, explaining, assigning and following up. The coordinator sets
its remit once: trusted documents, calendar scope, volunteer team, sending account
and communication cadence. The intended connected workflow runs routine work
without per-message approval; that end-to-end integration is not yet verified.
The persona and workflows use each organization’s own roles and supplied policies.

A member asks “What do I wear?” The agent checks the event, the person's role,
and the applicable supplied dress rules, then gives a direct answer with a
citation. The coordinator supplies a todo list. It allocates work using stated
skills, preferences, eligibility, availability and workload, queues notices and
reminders, and finds a replacement after a verified decline.

## Implemented and tested locally

- **Organizational knowledge:** document chunking and SQLite FTS5/BM25 retrieval,
  source/section citations, source replacement and audience filtering. OpenClaw
  generates answers from that evidence; no organization-specific rules are invented or bundled.
- **Dress rules:** reviewed rules with issuing body, section, version, event type,
  role, effective dates and review deadline. Conflicts, missing context and expired
  rules produce explicit unresolved states. Supported attire flows into reminders.
- **Calendar coordination:** complete scoped event snapshots, timezones, stable
  occurrence IDs, cancellations and changes. Updates invalidate unsent stale notices.
- **Autonomous reminders:** standing instructions authorize complete sourced
  templates automatically. Sender, audience, calendar scope, event categories,
  cadence and daily limit are checked. Optional manual review remains available
  for exceptional correspondence.
- **Task allocation:** opted-in volunteer profiles, stated proficiency, role
  eligibility, preferred/avoided categories, availability, maximum open tasks and
  overlap checks. Work is assigned and notices queued without individual approval.
- **Follow-through:** deduplicated assignment notices, task-reminder cadence,
  completion/cancellation handling and reassignment after verified declines.
- **Delivery state:** atomic claims and real provider receipts; uncertain outcomes
  are reconciled rather than blindly retried. Queued does not mean sent.
- **Deployment package:** digest-pinned Plow base, agent persona, four skills,
  MIT license, install guide and optional remote image build workflow.

**The initial snapshot passed 51 behavior tests locally.**
[The engineering audit](docs/AUDIT.md) records coverage, fix PRs and remaining
acceptance gaps. Run the suite for the current checkout rather than treating
this baseline count as its latest result. The combined audit changes passed 70 tests on Python 3.11–3.13 in
[GitHub CI](https://github.com/jjjhenriksen/good-company/actions/runs/36217186171).
The [remote image build and packaged-engine smoke test](https://github.com/jjjhenriksen/good-company/actions/runs/36217167986)
also passed at integration commit `3254ee9`. All five audit PRs are now merged
into `main`. Since that baseline, the native Plow runtime has been booted and the
real model has used the installed tools. Bounded fictional self-tests produced
verified calendar reads and four owner-loopback emails. The latest
[runtime upgrade evidence](eval/adoption/upgrade/README.md) verifies current code
and preserved state. No Good Company operational scheduler is enabled; unattended
delivery, external-participant reply identity and the full live lifecycle remain
unverified. See [scheduled acceptance](docs/acceptance/08-scheduled-cycle.md).

## Try it without credentials

Python 3.11+ with SQLite FTS5 is sufficient. No pip dependencies or model key.

```sh
python3 scripts/autonomous_demo.py
python3 scripts/demo.py
python3 -m unittest discover -s tests -v
```

The autonomy replay uses a clearly marked simulated date and fictional club,
people, addresses, dress rules and tasks. It shows sourced attire, automatic
reminder authorization, skill-based assignment, repeat-run deduplication and
reassignment after a decline. It performs no network calls or actual sends.
[Captured replay](docs/AUTONOMOUS-DEMO.txt).

Use tools through JSON request files:

```sh
python3 -m good_company.cli configure --input examples/profile.json
python3 -m good_company.cli configure-autonomy --input examples/autonomy.json
python3 -m good_company.cli set-dress-code --input examples/dress-code.json
python3 -m good_company.cli queue
```

The examples use non-deliverable `example.invalid` addresses. Never mistake them
for live operating instructions. `examples/team.json` and `examples/tasks.json`
contain request arrays; submit each entry individually through set-volunteer or
add-task. The demo handles these arrays directly.

State defaults to `.state/good-company.sqlite`; set `GOOD_COMPANY_DB` to a private
persistent path. Do not put real member information in this repository.

## Agent workflows

- [Community operations](skills/community-operations/SKILL.md): setup, standing
  remit, recurring loop, pause and operating brief.
- [Event coordination](skills/event-coordination/SKILL.md): scoped calendars,
  scheduling conflicts, reminders and delivery receipts.
- [Volunteer coordination](skills/volunteer-coordination/SKILL.md): opted-in
  profiles, task fit, assignments, declines and completion.
- [Organization knowledge](skills/organization-knowledge/SKILL.md): cited
  handbook/procedure answers and supplied role-specific dress rules.

[Adaptation guide](docs/ADAPTING.md): examples for food banks, arts nonprofits,
mutual aid, nonprofit boards and youth organizations, plus the skill migration map.
Job’s Daughters and the Bethel Guardian role are an intended use case, not a
built-in organizational model.

## Deployment and remaining work

[INSTALL.md](INSTALL.md) covers local setup and verification.
[Release checklist](docs/RELEASE.md) tracks publication.
[Conversational acceptance checks](docs/ACCEPTANCE.md) define the live tests.
[Implementation roadmap](docs/ROADMAP.md) defines the remaining integration and release work.

The base supplies texting and Google services through Latch on the owner's Mac.
A personal Apple/iCloud calendar needs an available Apple Calendar capability or
an explicit scoped export. Calendar normalization, incoming reply handling and
actual mail sends are performed by the OpenClaw agent using connected tools.
The local engine does not independently poll those services or send email.

The Dockerfile uses the public Plow base at commit
`1e73c82c4b3e0c9f76935bc0cc45061875b34aee`, pinned to manifest digest
`sha256:5f8ef7c3762b037420cd8843a767a7ab7e2433b1c8319e7cfe2ad1bdef5dee8a`.
Its five-minute Agent Index reporter is inherited. The operational scheduler is
a separate setup step and must be tested with the actual provider permissions.
If a connected provider requires approval on every send, that connection cannot
provide unattended delivery; the agent must report the limitation.

## Practical limits

This is a trusted single-organization assistant. The inherited runtime shell and
shared files are powerful; prompt-level audience filtering is not isolation from
hostile users. A public/member-facing deployment needs separately restricted
identities and tools. The current image should run as the coordinator's trusted
assistant. Participant-facing access needs enforced identity and tool boundaries.

“Strengths and weaknesses” means stated task fit, skill gaps, preferences and
capacity. The allocator does not infer personal/sensitive traits or publicly rank
people. Tasks can declare `role_match: ANY` or `ALL`; omitted values preserve legacy ANY
semantics. Required roles are supplied by the authoritative roster; the software
does not itself verify certifications. Its ranking is a simple deterministic
heuristic, not global schedule optimization.

Events can explicitly declare `dress_applicability: not_applicable` when there is
no attire requirement. Event-category authorization remains separate. `required`
and legacy/`unknown` typed events still require current, accessible, applicable
supplied rules; never invent a policy or infer not-applicable from a meeting title.

The engine supports a legacy global reminder audience and explicit per-program
audiences within the standing recipient list, complete normalized calendar JSON,
and immutable task definitions.
raw ICS recurrence parsing, dedicated RSVP extraction, automatic certificate/form
verification, travel-aware scheduling and general regulatory compliance checking
are not implemented. Already-delivered corrections and changed task assignments
require agent-led reconciliation through the connected tools. Unknown delivery
outcomes do not automatically retry.

Standing-instruction references and source-review references are audit records,
not cryptographic identity proofs. The local operator can change the database.
The agent must verify incoming sender identity before accepting a decline or
completion. The live acceptance tests must establish that it does so correctly.

The package contains no real Term Book, private calendar, roster, contact list,
or credential. Original code and instructions are MIT licensed; inherited
components keep their own licenses. This project is independent of JDI, Plow and
OpenClaw and does not imply organizational endorsement.
