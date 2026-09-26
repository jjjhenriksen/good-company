# Runtime acceptance attempt — 2026-09-26

Related issue: #7. The initial emulated boot failed; a pinned native ARM64 candidate subsequently booted and answered through the real Plow model.

A private local Plow deployment on an available line successfully built the pinned
base and created the service with a new dedicated state volume. The service
resolved its Plow identity, then exited with code 78 during OpenClaw migration.
No model reply, mail delivery, operational scheduler, or restart acceptance is
claimed. No recipient was contacted.

Observed versions:

- Plow base: `1e73c82c4b3e0c9f76935bc0cc45061875b34aee`
- Base manifest: `sha256:5f8ef7c3762b037420cd8843a767a7ab7e2433b1c8319e7cfe2ad1bdef5dee8a`
- OpenClaw: `2026.9.6 (eb377ac)`
- Linux container architecture: `x86_64`, running under Docker on Apple Silicon
- State owner: uid/gid 1000 (`node`), persistent directory writable by that owner

The gateway reported that shared-auth-store migration could not acquire the state
maintenance path. With the gateway stopped, an offline `doctor --fix` reported
`openat2 beneath root: Function not implemented (os error 38)`. A separate direct,
read-only syscall probe against `/tmp` also returned errno 38. This establishes an
incompatible syscall on this runtime; it does not establish that a native Linux
host passes or that every migration warning has the same cause.

The development build included in-progress onboarding work, so it is **not an
immutable release-commit verification**. Before acceptance, build the chosen exact
commit and record its image digest, pass the preflight on a compatible Linux host,
then observe boot, available tools, one real model response, and state after
restart. Keep line identifiers, credentials, account addresses and private logs
outside this repository. Do not mark downstream delivery/publication checks done
on the strength of this build or a fixture.

## Native ARM64 verification

A separate native build avoids the unsupported emulation syscall. It uses the
same Plow source, the official OpenClaw 2026.9.6 ARM64 manifest, and the official
agentsview 0.44.0 ARM64 artifact verified against its release SHA-256. The original
AMD64 Dockerfile remains available for compatible Linux hosts.

- Candidate source: `34e3a3c` (committed native preview build)
- Local immutable image ID: `sha256:04df13977cbe575be23f19ca9589c6b6c2a013d5a993ec7c3aba7a5fbbc1535c`
- Native preflight: Linux aarch64, `openat2` available
- Gateway: reached ready; Plow channel connected
- Model: real `plow/z-ai/glm-5.2` response, successful run recorded privately
- State: fictional organization profile survived a service restart; sending authority remained unconfigured
- Owner: uid/gid 1000; local Good Company tool executed successfully

The initial model response identified itself as Good Company. No external message
was delivered. Latch instructions remained unavailable, so this does not establish
calendar/mail acceptance, Agent Index registration, public release or unattended
scheduler delivery. The image ID identifies a local built artifact, not a public
registry manifest. Provider and publication work remains separate.


The post-restart model used local exec/read tools. It also encountered OpenClaw's
restriction on direct sqlite3 access beneath its managed state directory. The
preview now gives coordination its own `/var/lib/good-company` persistent volume;
existing installs must migrate the stopped database rather than start an empty
ledger. Revalidation of this final layout is recorded below when complete.
