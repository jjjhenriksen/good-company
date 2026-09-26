# Release and Agent Index handoff

Working identity:
- Name: Good Company
- Slug: good-company (not yet claimed or verified available on the Index)
- Blurb: An executive assistant for busy community leaders: knows the supplied rules, coordinates volunteers, and handles routine reminders.
- Runtime: OpenClaw on the Plow base

Repository: [jjjhenriksen/good-company](https://github.com/jjjhenriksen/good-company)
(currently private). [Audit and fixes](AUDIT.md); [remaining work](ROADMAP.md).

## Verified development checks

- Original coordinator persona, workflow skill, persistence tools, and MIT license.
- Fictional example knowledge and a credential-free demonstration.
- Behavior tests for retrieval, reminder state, changes, recipients, freshness,
  privacy of conflict output, and duplicate-send claims.
- Base digest resolved from the public ECR registry on September 25, 2026.
- Plow account login confirmed during the build. No credential is in this repo.

## Required before publication

- [x] Build the combined audit image and smoke-test its packaged CLI/database remotely (integration commit `3254ee9`; see AUDIT.md).
- [ ] Boot the full runtime on a selected free Plow line and receive a real text reply.
- [ ] Verify inherited Latch capabilities with the intended calendar/mail accounts.
- [ ] Verify one complete scoped calendar import and a changed/cancelled occurrence.
- [ ] Configure standing instructions for a test audience; verify an automatic reminder and receipt without per-message review.
- [ ] Verify event/role-specific dress answers against supplied sources.
- [ ] Verify skill-based assignment, notices, verified declines and reassignment.
- [ ] Verify one scheduler run and no duplicate delivery on the next run.
- [ ] Claim the Index slug and verify reporting after genuine model activity.
- [x] Create the source repository with MIT LICENSE and conventional feature commits.
- [ ] Review the audit PRs and publish the currently private repository; record the exact release commit.
- [ ] Record a demo video using fictional data and no credentials or private membership content.
- [ ] Capture at least one image of the working agent; choose an optional logo.
- [ ] Publish the image and make it publicly pullable.
- [ ] Register video, screenshot and install URL on the Index.
- [ ] Request verification and 1-click admission in Discord.

Do not check an item merely because a command was attempted. A source test, image
build, running container, model reply, provider send, accepted usage report and
public listing are distinct receipts.

## Build without using local Docker disk

The repository contains a manual GitHub Actions workflow at
`.github/workflows/build-image.yml`. After creating a repository, run **Build agent
image** from its Actions page. It builds/tests on the runner. Publishing is an
explicit workflow input; the default builds without pushing. A successful image
build is still not runtime or texting verification. For a first GHCR push, make
the package public in GitHub settings before asking Plow to pull it.

## Register complete media

Once real media URLs and a public repository exist, run the inherited client
inside the agent (replace every uppercase placeholder):

```sh
docker compose exec -e HOME=/var/lib/plow agent \
  python3 /opt/plow/agent-index-client.py --register \
  --agent good-company --name 'Good Company' \
  --blurb 'An executive assistant for busy community leaders: knows the supplied rules, coordinates volunteers, and handles routine reminders.' \
  --runtime OpenClaw \
  --repo REPOSITORY_HTTPS_URL \
  --video YOUTUBE_VIDEO_ID \
  --image SCREENSHOT_HTTPS_URL \
  --install-url INSTALL_GUIDE_HTTPS_URL
```

`--video` is a YouTube video ID, not a full URL. Use the client's existing state
on `/var/lib/plow` so registration does not invent a second install identity.
The base reporter remains responsible for the five-minute usage schedule.

## Public image and 1-click admission

```sh
plow-agents image build ghcr.io/YOUR_ACCOUNT/good-company:v1
plow-agents image push ghcr.io/YOUR_ACCOUNT/good-company:v1
plow-agents profile --show
```

Use the exact digest reference printed by push. An admin needs the builder UID,
slug and public image reference to admit the first release. Also provide the
repository, commit hash and Agent Index ID in the verification thread. The CLI
cannot grant that admission to itself. No Discord message has been sent.

After admission, future releases use:

```sh
plow-agents image push ghcr.io/YOUR_ACCOUNT/good-company:v2 --promote good-company
```

## Demo outline

1. “Our team has a calendar and a handbook. People still ask the same questions,
   and someone still has to remember to send every email.”
2. Ask the agent what to bring; show its source citation.
3. Ask for upcoming reminders; show a draft based on a real fictional calendar event.
4. Show the standing remit and verify a routine test message arrives without a per-message approval.
5. Supply a todo list; show suitable task allocation and reassignment after a verified decline.
6. Change another event's location; show the old draft is superseded.
7. Run the queue again; show no duplicate send.
8. Close with the actual installation steps and how the coordinator configures or pauses the remit.

## Source references checked

- [Publish instructions](https://aiworthusing.com/agent-index/publish)
- [OpenClaw base](https://github.com/plow-pbc/plow-openclaw-agent), commit `1e73c82c4b3e0c9f76935bc0cc45061875b34aee`
- [Plow CLI](https://github.com/plow-pbc/plow-agents), commit `3033a59754067bb21b4b6b2844967db343ecf7bd`
- [Agent Index client](https://github.com/plow-pbc/agent-index-client)
- [OpenClaw automations](https://docs.openclaw.ai/automation/cron-jobs/managing-jobs)

Recheck deadlines and eligibility on the organizer's current event page before
submission. The website and calendar invitation may differ; this project does
not treat a cached date as an authoritative deadline.
