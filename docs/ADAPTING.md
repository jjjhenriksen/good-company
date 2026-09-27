# Adapt Good Company to your organization

Good Company is a trusted coordinator’s assistant for a small nonprofit or
volunteer-led team. Choose the organization’s language and supplied sources;
there is no built-in governance model or universal set of nonprofit rules.

## Four skills, selected by the work

| Request | Skill | Result |
|---|---|---|
| “Set us up; keep routine work moving; pause reminders” | [community-operations](../skills/community-operations/SKILL.md) | Profile, standing remit, verified scheduler and brief |
| “What’s next? Remind our team; find a time” | [event-coordination](../skills/event-coordination/SKILL.md) | Scoped calendar, reminder ledger, conflict check |
| “Assign these jobs; someone declined; mark this done” | [volunteer-coordination](../skills/volunteer-coordination/SKILL.md) | Eligible assignments and task notices |
| “What’s our policy? What do I bring or wear?” | [organization-knowledge](../skills/organization-knowledge/SKILL.md) | Cited answer or a precise evidence gap |

Start with organization/timezone, the coordinator’s preferred title, one useful
source, an exact calendar scope and a verified sending account/audience. Add
volunteer opt-in, roles, skills, preferences and availability when delegation is
needed. Configure standing authority once; routine work within it does not need
per-message approval. Verify the real provider permits unattended sends.

The profile stores organization, timezone, greeting, signoff, audience, cadence
and send hour. Preferred title and broader vocabulary are conversation context,
not additional implemented profile fields. Role and event-category labels come
from the organization. They must match across calendar imports, rules, roster,
tasks and the standing remit. Examples are fictional request shapes, never real
authority. They ship at `/opt/good-company/examples/` in the image.

## Representative use cases

These are adoption scenarios, not completed deployments or supplied policies.

| Organization | Useful first workflow | Sources to supply | Current boundary |
|---|---|---|---|
| Food bank | Assign a packing shift and answer arrival/supply questions | Local shift guide, authorized roster, actual training requirements | No certification expiry or multi-person staffing model |
| Arts nonprofit | Prepare a rehearsal brief and delegate venue preparation | Production calendar, venue instructions, volunteer availability | One event audience per instance; no event-linked task rescheduling |
| Mutual aid group | Allocate a scoped todo list and follow up with opted-in helpers | Operating guide and approved task/contact details | No beneficiary case management, public intake or route optimization |
| Youth organization, including Job’s Daughters | Support a Guardian or other leader with sourced attire answers and event preparation | Current applicable rules, reviewed extracts, calendar/term book and authorized roster | No invented governance hierarchy or automatic safeguarding-compliance certification |
| Small nonprofit board | Find a meeting time and retrieve procedure answers | Availability and current board procedures | Automatic typed reminders currently require dress-rule resolution, even if attire is irrelevant |

A real organization can use multiple workflows. Avoid importing private source
material simply to imitate the demo. Generalize the workflow, not another group’s
rules. Dress requirements are relevant where supplied; a missing dress policy
must not be turned into a fictional requirement. Separating dress applicability
from event authorization is the first portability change in [ROADMAP.md](ROADMAP.md).

## Existing installation migration

| Earlier skill | Current owner of that work |
|---|---|
| `autonomous-guardian` | `community-operations` for remit/scheduler; `volunteer-coordination` for roster/tasks |
| `community-coordinator` | `event-coordination` for calendar/delivery; `organization-knowledge` for retrieval; `community-operations` for setup |
| `guardian-support` | `organization-knowledge`, with the dress workflow in its references |

The CLI, policy fields and database schema are unchanged. Do not reset the state
volume, receipts, install identity or standing instructions to rename skills.
Back up persistent state privately before replacing a deployed image. Inspect
how the actual runtime loads custom skills: if it preserves copied skill files,
remove only the three obsolete custom skill directories after verifying the four
new ones are installed; do not remove inherited Plow skills. Update any saved job
instructions that refer to old skill names, keeping the existing job ID and remit.
Verify one job remains, its permissions and next run are correct, and a controlled
test produces no duplicate messages. New image builds contain only the new custom
skill names. The [live upgrade acceptance](acceptance/57-runtime-upgrade.md)
now verifies saved state, loaded skills, install identity and one duplicate-free
post-upgrade scheduled tick for the documented local image replacement.
