# Install Good Company

## 1. Requirements

Python 3.11+, Git, Docker with Linux/amd64 support and Compose 2.24+, sufficient
free disk space for the OpenClaw image, and a phone for Plow activation.
For live Google email/calendar access, connect the owner's Mac through Latch.

Try `python3 scripts/demo.py` first; it needs no account or Docker image.

## 2. Get the source and Plow CLI

The source is public. The exact published Linux AMD64 image and anonymous-access
evidence are in [the release record](docs/acceptance/12-release-gate.md).

```sh
git clone https://github.com/jjjhenriksen/good-company.git
cd good-company
```

Use a Python interpreter that reports version 3.11 or newer. Some Macs still
resolve `python3` to the system Python 3.9; select the supported interpreter
explicitly for all local commands in that case.

Use the official [plow-agents repository](https://github.com/plow-pbc/plow-agents).
Keep that checkout beside, not inside, Good Company's Docker build context.

```sh
git clone https://github.com/plow-pbc/plow-agents.git ../plow-agents
export PATH="$PWD/../plow-agents/bin:$PATH"
plow-agents login
plow-agents lines
```

Login prints a phrase and number: text that phrase from your phone. Login stores
an account token on your machine, never in this image. Select a line currently
shown as `free`; do not assume `ln_p1` will remain free.

## 3. Run a private preview

Before allocating a Plow line, create the environment file required by Compose
if it does not exist. This preserves any existing credentials:

```sh
if [ ! -e plow-credentials ]; then (umask 077; touch plow-credentials); fi
```

Then build and check runtime compatibility:

```sh
docker compose build agent
docker compose run --rm --no-deps --entrypoint python3 agent /opt/good-company/runtime_preflight.py
```

A passing result only checks syscall support. An `openat2`
`Function not implemented` failure means this Linux emulation cannot run the pinned
OpenClaw state filesystem. Use a compatible Linux host. Do not bypass filesystem
containment, repeatedly reset the state volume, or count the build as a live boot.
For the tested native Apple Silicon preview, add `-f compose.arm64.yml` to the
Compose command after `-f compose.yml`. For example:

```sh
docker compose -f compose.yml -f compose.arm64.yml build agent
docker compose -f compose.yml -f compose.arm64.yml run --rm --no-deps --entrypoint python3 agent /opt/good-company/runtime_preflight.py
```

Use the same file pair for startup, logs, stop and restart. Mint the selected Plow
line's credential with `plow-agents mint LINE_ID`, then start this native Compose
configuration directly; the generic `deploy --local` command uses the default
AMD64 file. The native path passed boot, actual model-response and restart-state
checks. Scoped Google calendar/mail, actual delivery and lifecycle checks are
recorded in [the acceptance evidence](docs/acceptance/09-lifecycle-acceptance.md);
a new installation must verify its own account and authority.
The initial Apple Silicon x86-emulation attempt hit this failure; see
[the runtime evidence](docs/RUNTIME-VALIDATION.md).


From this project directory, replacing LINE_ID with that free line:

```sh
plow-agents deploy --local --line LINE_ID
docker compose ps
docker compose logs --tail 100 agent
```

Compose builds Linux/amd64 and uses separate named volumes for OpenClaw runtime
state and Good Company coordination data. This keeps the app database outside
OpenClaw's protected managed-state directory while preserving it across restarts. The dashboard is
[localhost:3007](http://localhost:3007). It is loopback-only and grants local
operator access. Do not expose that port to other machines. The proxy accepts only localhost and
127.0.0.1 Host names and the documented local Origin values, removes caller-supplied
forwarded identity headers, and assigns the development owner identity itself.
These are local-development checks, not public multi-user authentication.
`python3 scripts/check_proxy.py` exercises these behaviors against the pinned Caddy
image with a fictional echo backend and an ephemeral loopback port.

Local Compose deliberately overrides `AGENT_ID` to empty unless you set it, so
previewing does not claim a public listing. Cloud installs use the Dockerfile's
baked `good-company` id and inherited five-minute reporter.

Text the selected line. Verify a real answer before proceeding. In the dashboard
or owner conversation, provide an organization profile, document sources, and
calendar scope. Use fictional data until connection and authority are verified.

## 4. Connect and verify

Ask Good Company to list the available Mac skills and follow their setup path.
The inherited google-workspace skill uses Google services through Latch; do not
add local OAuth credentials to the image. Confirm the actual sending account,
calendar, audience and timezone. An Apple/iCloud calendar needs its own available
capability; otherwise use a scoped export and keep the workflow in draft mode.

For a personal calendar, use an explicit organization-only scope. Import all
instances in its date window, with stable IDs and all pages. Do not label a
partial title search a complete snapshot. The agent's source selection and
calendar normalization must be verified with a known event and a known change.

## 5. Enable reminders

Ask the owner-session agent to set up the reminder schedule using
[the operations skill](skills/community-operations/SKILL.md). It must inspect
`openclaw cron add --help` on the pinned runtime, reuse an existing matching job,
create one queue-check schedule, and verify the saved job and a test run.

Configure the standing remit using the community-operations skill: sender,
audiences, calendar/event/task scopes, cadence and volunteer preferences. The
scheduler refreshes sources, automatically authorizes complete routine reminders
within that remit, allocates tasks, sends due notices and records real receipts.
It does not need per-message coordinator approval. Incomplete or conflicting items
remain exceptions for the agent to investigate. If
Latch requires a fresh interactive approval, automatic sending remains unavailable;
the agent can still prepare drafts and ask for the necessary action.

First live test: configure one test recipient and event in the standing remit.
Verify the whole loop without approving each generated message. Verify one
received message, a receipt, a second run producing no duplicate, and an event
change invalidating an unsent reminder. Do not test with a membership list.

## 6. Publish when verified

See [the release checklist](docs/RELEASE.md). Set the listing slug only after
checking its availability/ownership with the Index. A missing Plow catalog row
alone is not proof that an Index slug is unclaimed.

```sh
AGENT_ID=good-company docker compose up -d
# Inspect reporter logs and verify real usage after a model conversation.
docker compose logs --tail 100 agent
```

The reporter inherits persistent install identity and measures OpenClaw usage.
A running container alone does not prove usage was accepted by the Index.

## Stop and resume

`docker compose down` stops the local preview and preserves its state volume.
`docker compose up -d` resumes it. Avoid `down -v`: it deletes the coordination
history and reporting install identity. Back up the named volume privately.

For organization-specific terminology, use cases and upgrading the renamed skills,
see [the adaptation guide](docs/ADAPTING.md).


### Migrating an existing coordination database

Stop the gateway and scheduler before changing volumes. Earlier previews stored
`good-company/state.sqlite` inside the Plow state volume. Back up that entire
volume privately, then use SQLite's backup API to copy the stopped coordination
database into the new coordination volume as `state.sqlite`, owned by uid/gid 1000
with mode 0600. Keep the old database and backup until the migrated policy and
receipts are verified. Never initialize a replacement empty ledger for an existing
installation: it would lose deduplication history. Back up both volumes together
while stopped; the runtime volume retains the reporter install identity.
