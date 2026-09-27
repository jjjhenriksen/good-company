# Native runtime acceptance — 2026-09-26

Issue #7: verified on an available private local Plow line, using fictional data.

| Observation | Evidence |
| --- | --- |
| Exact committed candidate | `4bdee43` |
| Local immutable image | `sha256:7876a480bb3badaeea7248aabf03ec41f6b0fb3bf4796fccd59e9c1247db9120` |
| Plow source | `1e73c82c4b3e0c9f76935bc0cc45061875b34aee` |
| OpenClaw | `2026.9.6 (eb377ac)`, pinned official ARM64 manifest |
| Runtime | Docker Linux aarch64 on Apple Silicon; openat2 preflight passes |
| Ownership | Runtime and coordination volumes writable by uid/gid 1000 |
| Boot | Gateway ready and Plow channel connected |
| Real model | `plow/z-ai/glm-5.2`, completed run, exec/read tools available |
| Installed tool | Model invoked `good-company profile` and `good-company autonomy` successfully |
| Stored result | Fictional Good Company Demo Club; America/Los_Angeles; autonomy null |
| Restart | Same profile read successfully after restarting the candidate container |

Private raw run receipts remain outside the repository. The model correctly read
settings via the installed command; empty retrieval results are not setup evidence.
No recipient was contacted and sending authority remains unconfigured.

The original AMD64 base under emulation failed OpenClaw state migration because
openat2 returned errno 38. The native preview preserves pinned Plow source and
OpenClaw versions, rebuilding native dependencies and verifying the ARM64
agentsview download checksum. It does not disable the filesystem safety check.

Live testing also exposed the tool environment dropping PYTHONPATH. The installed
launcher now sets its own import path. Coordination state has its own persistent
volume; a stopped fictional database was migrated using SQLite backup and verified
before restart. Startup refuses an old nonempty ledger paired with missing/empty
new state; INSTALL.md describes migration without deleting the original.

The image digest above is a local built artifact, not a public registry manifest.
The final documentation commit records the tested code commit; it does not change
runtime files. Google connected-tool discovery still returns HTTP 503 after native
restart. Calendar/mail delivery, operational scheduling, public release and Agent
Index acceptance remain separate, unverified requirements.
