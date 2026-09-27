# Release and Agent Index handoff

Working identity:
- Name: Good Company
- Slug: good-company ([owned listing](https://aiworthusing.com/agent-index/good-company); genuine usage accepted)
- Blurb: An executive assistant for busy community leaders: knows the supplied rules, coordinates volunteers, and handles routine reminders.
- Runtime: OpenClaw on the Plow base

Repository: [jjjhenriksen/good-company](https://github.com/jjjhenriksen/good-company)
(public). [Audit and fixes](AUDIT.md); [remaining work](ROADMAP.md).

## Verified development checks

- Original coordinator persona, workflow skill, persistence tools, and MIT license.
- Fictional example knowledge and a credential-free demonstration.
- Behavior tests for retrieval, reminder state, changes, recipients, freshness,
  privacy of conflict output, and duplicate-send claims.
- Base digest resolved from the public ECR registry on September 25, 2026.
- Plow account login confirmed during the build. No credential is in this repo.

## Readiness and remaining publication work

- [x] Full runtime boot, genuine model reply and persistent state: RUNTIME-VALIDATION.md.
- [x] Scoped Google account/calendar/mail acceptance and actual scheduled delivery: acceptance/08-scheduled-cycle.md and GOOGLE-ADAPTER-VALIDATION.md.
- [x] Live source change, cancellation/restoration, owner-loopback decline/completion and pause checks: acceptance/09-lifecycle-acceptance.md. External participant identity remains issue #29.
- [x] Genuine sourced role/dress answers: eval/adoption/youth/model-result.json.
- [x] Conversational setup and preserved runtime/Index identity after upgrade: ONBOARDING-VALIDATION.md and acceptance/57-runtime-upgrade.md.
- [x] Owned Index slug and automatic genuine usage reports: acceptance/14-index-usage.md.
- [x] MIT source and recorded fictional demo/screenshot: media/README.md.
- [x] Candidate source/history, build-context and media review: acceptance/12-release-gate.md.
- [x] Publish reviewed source and smoke-tested image; exact commit/digest in acceptance/12-release-gate.md.
- [x] Verify anonymous source/image access and public-image package checks.
- [x] Register public video, screenshot and install references on the Index.
- [ ] Obtain organizer verification and one-click admission.
- [ ] Complete fresh-user published-install acceptance (issue #16).

Live eligible reassignment and real pilot scenarios remain tracked in issues
#29, #41 and #58–61; owner-loopback and fixture checks do not complete those.
A source test, image build, running container, model reply, provider send,
accepted usage report and public listing are distinct receipts.

## Build without using local Docker disk

The repository contains a manual GitHub Actions workflow at
`.github/workflows/build-image.yml`. After creating a repository, run **Build agent
image** from its Actions page. It builds/tests on the runner. Publishing is an
explicit workflow input; the default builds without pushing. Both paths load the
built image and verify its installed commands, paused cycle, skills, examples and
MIT notice before any push. Publishing pushes that exact tested local image and
records the registry digest in the workflow summary. A successful image
build is still not runtime or texting verification. For a first GHCR push, make
the package public in GitHub settings before asking Plow to pull it.

Before publication, `python3 scripts/check_image_engine.py IMAGE` also verifies
that every installed coordination module matches the selected checkout, then runs
the full regression suite and both fictional demos inside the image. It mounts
only tracked tests/support files, uses packaged examples, disables networking,
and confines writes to temporary storage with a read-only root filesystem. The
source engine and credentials are not mounted. This check runs automatically in
the image workflow; it still does not establish live provider delivery or a model
reply.

The Docker context uses exact file entries in `.dockerignore`. Add new runtime
files explicitly; do not replace them with directory exceptions, which also admit
unexpected local descendants. Run `python3 scripts/check_build_context.py` from a
Git checkout after changing runtime files or either Dockerfile. It copies only
fictional canaries into a scratch build and checks Docker's actual exclusions
against the tracked COPY inputs. CI and the image workflow run this check before
building or publishing. It verifies context boundaries, not the contents of an
intentionally admitted source file.

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
