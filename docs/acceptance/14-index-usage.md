# Index identity and usage acceptance (#14)

Observed 2026-09-26: the official Index endpoint
`https://agent-index-server.vercel.app/v1/agent?agent_id=good-company` returned HTTP
404 with `{ "ok": false, "error": "no such agent" }` (error/status observed; do not
infer lasting availability). No ownership claim or accepted usage receipt exists.
The local preview deliberately leaves AGENT_ID empty. Real model runs occurred,
but that does not prove Index ingestion.

Using the authenticated maintainer identity, recheck then claim/update the intended
slug with the inherited supported client. Verify ownership from the actual response,
not merely an absent Plow catalog entry. Preserve the existing install identity.
Enable the inherited reporter for that owned slug, run a genuine model conversation,
and record an accepted report plus the matching listing usage observation. Restart
and confirm the same install identity and scheduled reporting without duplicate
install registration. Do not submit synthetic token counts or replay fixture usage.

Pending evidence: authenticated ownership receipt, report acceptance, listing usage
and post-restart reporting. No slug was claimed or public metadata changed here.
