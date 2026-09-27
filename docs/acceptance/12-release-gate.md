# Public release gate (#12)

Status: lifecycle dependency #9 passed and closed in PR #142; runtime dependency
#11 is also closed. Publication remains pending. The MIT repository is private
as of this review on 2026-09-26. Native runtime evidence and provider acceptance
are recorded separately; a local image ID is not a public registry manifest.

## Content review before publication

Reviewed candidate: `ce2c1b6e967edfd4e3b5436720103a97bc9f1c7c`.

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
  preserves their notices, with Good Company's MIT LICENSE copied into the image.
- Visually reviewed all six pages of the two bundled fictional PDFs and the agent
  screenshot. Reviewed video metadata and frames sampled every three seconds:
  fictional scenarios, no audio stream, no observed private account or credential.
  This is a sampled video review, not a frame-by-frame attestation.
- The 383 behavior tests and packaged-image smoke checks remain mandatory before
  any registry push. The final release record must identify the published commit,
  build run and registry digest, rather than substituting this candidate review.

Release sequence:
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
