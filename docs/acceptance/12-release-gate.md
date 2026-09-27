# Public release gate (#12)

Status: blocked by live delivery/lifecycle acceptance (#9). Current repository
visibility is PRIVATE and the license is MIT (verified 2026-09-26). Native local
runtime evidence exists in RUNTIME-VALIDATION.md; a local image ID is not a public
registry manifest. No public source/image release has been performed.

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
boundary reviewable while provider-dependent acceptance remains unresolved.
