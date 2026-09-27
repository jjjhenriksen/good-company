# Optional participant evidence boundary

The owner Plow agent remains privileged. Do not connect participants to its chat,
shell, files or operator CLI. `python -m good_company.participant --config PRIVATE_FILE`
is a separate, opt-in loopback HTTP service with exactly one operation:
`POST /v1/evidence`, JSON question and optional ISO date. It returns public/volunteer
source evidence and citations; it does not run a model, shell, provider or mutation.
Retrieved text is inert data. No public or member channel is enabled by this PR.

The private configuration maps organization IDs to separate SQLite paths and holds
`credentials` entries with sha256, organization, role=participant, and optional
disabled. Generate independent random bearer tokens with at least 32 random bytes;
store only their SHA-256 hashes here. Distribute/revoke tokens through the owner's
existing authenticated identity process. Token possession authenticates access;
there is no self-registration or client-selected organization/role. Configuration
reloads on each request, so revocation applies immediately. Keep file permissions
private; do not use the short fictional tokens in tests.

Before external access, provide authenticated enrollment, TLS termination and
rate limits at a separately reviewed gateway. Never put bearer tokens in URLs or
logs. The service deliberately binds only to 127.0.0.1 and reads organization
state using SQLite read-only mode. It cannot safely be substituted with the owner
agent plus a prompt instruction. Answers generated elsewhere must treat returned
sources as data and retain this same restricted boundary.
