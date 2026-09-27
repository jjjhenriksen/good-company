# Runtime third-party notices

These unmodified license and notice files accompany software inherited from the
pinned Plow/OpenClaw runtime. `manifest.json` records exact upstream revisions and
SHA-256 hashes. Good Company source is MIT; bundled components retain their own
licenses, including the Apache-2.0 Agent Index client.

Both Docker variants place this directory at `/opt/good-company/third_party`.
The base image also retains its dependency license files in their original
locations. These copies supplement those files rather than replacing them.

OpenClaw 2026.9.6 and agentsview 0.44.0 match the versions selected by the pinned
Plow base and native override. Update the notices and manifest whenever those
components change. Packaged-image smoke checks compare every file with source.

## Agent Index compressed-event compatibility

Both image variants override the inherited standalone reporter with the unmodified
client from upstream PR #17, commit `7d42f568faecfbbdea9ff0f16d66d43f68dce02f`.
This is an explicitly pinned, not-yet-merged upstream revision. It decodes OpenClaw
schema-23 Zstandard events instead of silently dropping their usage. Legacy plain
rows still work; unreadable compressed events block a partial report. Its original
Apache-2.0 license, notice, source URL and byte hash are retained here.

The installed-image regression suite exercises mixed/legacy stores, duplicate
response IDs, missing decoders and corrupt-event refusal against the actual
`/opt/plow/agent-index-client.py`. Fixtures are fictional, isolated and offline.
Credentials, install identity, endpoints and the inherited reporting schedule
are unchanged. Replace the pinned revision deliberately when upstream merges a
reviewed update; do not fetch a floating branch during image construction.
