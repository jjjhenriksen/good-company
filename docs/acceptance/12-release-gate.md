# Public release gate (#12)

Status: passed public source and image acceptance on 2026-09-26 (Los Angeles).
Lifecycle dependency #9 and runtime dependency #11 are complete.

- Release commit: `b64fd87e2e3c2d9e809bea2490fb922b5991d00c`.
- Public image (Linux AMD64): `ghcr.io/jjjhenriksen/good-company@sha256:dca7799e517f94d64865b387ac175ba57f188124fc8fb98b1b403b65c63d77b4`.
- [Exact-commit CI](https://github.com/jjjhenriksen/good-company/actions/runs/36293277911): all three Python jobs passed, including 383 behavior tests, demos, wheel and proxy checks.
- [Publish workflow](https://github.com/jjjhenriksen/good-company/actions/runs/36293287680): attempt 2 passed. The first attempt hit an upstream ECR HTTP 429 before building; retry retained the exact pinned base. The image passed installed-command, paused-cycle, skills/examples and exact license/notice checks before push.
- Anonymous repository API, exact-commit LICENSE, Git read and clean source clone succeeded. The documented fictional demo passed in that clean clone.
- Anonymous Docker pull of the digest succeeded using an empty auth configuration. The pulled image passed installed paused-cycle and exact license/notice checks without networking. The package page identifies it as Public.
- Public screenshot and MP4 downloads matched their recorded hashes.

See [machine-readable release evidence](../../eval/providers/public-release.json).
The anonymous image smoke ran under Apple Silicon AMD64 emulation; it does not
claim a full runtime boot. Genuine native runtime acceptance remains separately
recorded. Fresh-user model/provider/state acceptance is #16, and organizer
verification/one-click admission is #15.

## Content review before publication

Reviewed candidate: `ce2c1b6e967edfd4e3b5436720103a97bc9f1c7c`. Final release refresh
covered all 199 tracked files and 494 historical blobs with no heuristic matches;
the added notices matched immutable upstream source revisions.

- Scanned all 192 tracked files and 479 historical blobs for known private test
  account details, private keys, GitHub tokens and owner-machine paths; no matches.
  The tree also passed the configured literal API-secret patterns. These are
  heuristic scans, not a guarantee against every possible encoded secret.
- Scanned GitHub issue/PR bodies, issue comments and review comments for the same
  private-account, key, GitHub-token and local-path indicators; no matches.
  Existing author attribution and Git commit identities remain part of the source.
- Inspected the actual Docker build context from the exact tracked tree. Runtime
  code, skills and fictional examples enter the context; private local credentials
  and acceptance databases do not. The image inherits the pinned base layers and
  preserves their existing notices, with Good Company's MIT LICENSE copied into
  the image. Review found missing top-level inherited runtime notices; the release
  adds exact OpenClaw, agentsview and Agent Index client notices under
  `third_party/`, with immutable upstream references and package checks.
- Visually reviewed all six pages of the two bundled fictional PDFs and the agent
  screenshot. Reviewed video metadata and frames sampled every three seconds:
  fictional scenarios, no audio stream, no observed private account or credential.
  This is a sampled video review, not a frame-by-frame attestation.
- The 383 behavior tests and packaged-image smoke checks remain mandatory before
  any registry push. The final release record must identify the published commit,
  build run and registry digest, rather than substituting this candidate review.

## Future release sequence
1. Freeze a commit after required tests and connected lifecycle/readiness acceptance.
2. Review the exact tracked tree and history for credentials and private pilot data;
   inspect binaries as well as text. Keep fictional fixtures clearly labelled.
3. Preserve MIT and inherited Plow/OpenClaw/dependency notices; record their pinned
   image/source references. Review the complete publishable artifact, not only diffs.
4. Deliberately publish source and build/push the tested image through the documented
   workflow. Record the returned immutable registry digest and make the package public.
5. Verify anonymous repository access and anonymous image manifest/pull from a clean
   Docker configuration. Private authenticated pulls do not satisfy this check.
6. Boot that digest, confirm model/tool/state acceptance, then update the release
   record with commit, digest, CI and anonymous-access receipts.

Never publish a fixture receipt as live validation or change visibility merely to
make downstream checkboxes appear complete. This plan makes the release evidence
boundary reviewable while public-access and fresh-install acceptance remain unresolved.

## Preview v0.1.1 — September 27, 2026

[Release v0.1.1](https://github.com/jjjhenriksen/good-company/releases/tag/v0.1.1)
uses reviewed merged source `5fa457253781a5d95680d2e7a9bda31d0128b6f5` and public image
`ghcr.io/jjjhenriksen/good-company@sha256:438548cc74a5fcc79323c4d1b20cffe6780220e8b4576b1a7dcd6d615c524ce8`.
[Publication run 36332812906](https://github.com/jjjhenriksen/good-company/actions/runs/36332812906)
passed all 479 installed-image tests, both demos, package integrity and Docker
context checks, then pushed that tested image. Anonymous manifest/config reads
verified its digest and Linux AMD64 platform. The compressed transcript reporter
fix from PR #193 is included in this image.

The owner promoted the new digest through the official Plow CLI; both Plow and
Index updates were acknowledged. The public Index read omits the image field;
the Plow readback independently confirmed the exact new digest. A separate hosted deployment reached `running` but full
fresh-user acceptance is still incomplete; see [#16 evidence](16-fresh-install.md).
No existing runtime was upgraded by promotion. The release remains a preview.
