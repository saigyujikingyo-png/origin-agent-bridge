# Connection recovery 0.2.15 candidate evidence

Date: 2026-10-14. Product-owned repair candidate. Full source, packaged installation,
selected host route and real workstation OS events are separate acceptance gates.

## Confirmed incident and repair

The host returned `Tunnel-client has not been seen for 300 seconds`. Both managed
local tasks were running, and the previous supervisor claimed local readiness.
The selected personal route's official client was repeatedly receiving HTTP 401
with `invalid_api_key`; its current daemon had no successful control-plane poll.
The other account had fresh successful polling. Encrypted credential files were
unchanged from the prior installation receipt, and a private comparison confirmed
that each running daemon used its saved credential. No credential appears here.
This establishes an authentication failure for this incident, without attributing
its origin to a user key change or to sleep.

The new observer checks the exact owned client's passive health snapshot, with
bounded loopback-only reads and sanitized fields. Local readiness cannot conceal
remote rejection. A retry in progress cannot reuse a successful poll from before
the latest failure; readiness requires a newer success. Current 401/403 stops the owned chain and blocks repeated launches
with that encrypted credential revision. A masked local repair window allows a
valid credential to be saved without changing plugin/account/tunnel identity.

Network retries preserve the existing owner. A confirmed idle poll stall can be
reconciled after a grace period; active or uncertain work is preserved. Independent periodic
repetition and resume/network-connected events request the same singleton startup.
Explicit stop and installation fences remain authoritative. No connection event
submits or replays a scientific job.

## Verification layers

| Layer | Evidence | Boundary |
| --- | --- | --- |
| Source regression | 383 passed, 2 skipped in 321.81 seconds; Ruff and offline lock checks passed. Skips require Windows link privileges | Does not certify OS sleep/reboot or all hosts |
| Package | 327 file hashes and 43 source/dependency fingerprints verified; identical ZIP/MCPB SHA-256 `437df5451213c55bc095f0ddf88debf6e888e709135f52efd5a5beae15cac589` | Local candidate; this report is updated after packaging |
| Official client | Pinned and SHA-verified 0.0.15 against an isolated loopback control plane: authentication rejection, TCP disconnection/recovery, and exact daemon pause/resume | No workstation network outage or OS sleep was induced |
| Ownership recovery | Confirmed idle stall replaces only its own chain; other account remains live; manual stop wins; a changed credential is not blocked by an older attempt | Controlled real-process fixtures |
| Windows scheduler | Production event/repetition/IgnoreNew XML registered and read back; a separate real timer fixture automatically ran twice after successful exit, without logon or manual start, then was removed | Timer execution used a one-minute interval; real OS resume/reboot/network events remain separate |
| Credential window | Password masking and non-writing validation verified with Windows PowerShell 5.1 | User must supply a valid key locally; automatic retries cannot fix rejection |
| Historical wake evidence | Pre-upgrade school-client logs show successful polling after an actual Modern Standby resume on this date | Historical 0.2.13 observation, not 0.2.15 or selected-host acceptance |
| Installed | Controlled 0.2.15 upgrade passed the synthetic native read-back gate. Both account identities, encrypted credentials, enabled/stop intent and all 23 original mini-project file hashes were preserved. Both tasks have an independent next scheduled run | Both saved keys currently return `invalid_api_key`; selected-host acceptance remains blocked |
| Actual reboot/logon/sleep/WAN restoration | Pending a safe workstation event and post-event selected-host call | No automatic disruptive workstation test |

## Dependency and remaining gates

The verified dependency remains official tunnel-client 0.0.15. Upstream 0.0.16
release changes do not establish a repair for this authentication incident;
changing the pinned dependency is not required for this scoped patch.

The one-plugin goal requires a powered, logged-in online computer, a valid personal
connection and the licensed Origin runtime. The repair removes routine manual
reconnect steps for recoverable connection failures; it cannot bypass authentication.
A fresh successful selected-host `origin_status` call, actual reboot/login and
sleep/wake recovery, and long-duration behavior must be recorded before claiming
those gates passed. The earlier unexplained `0xC000013A` exit and external local
Work project-sync issue remain unresolved/out of scope respectively. Scientific
and artifact-delivery acceptance remains separate.

Private identities, encrypted credentials, logs and installation receipts stay
outside public source. Package checksums are distributed alongside the candidate.
No GitHub release or universal host support is claimed by this report.

Primary references: [official client](https://github.com/openai/tunnel-client/releases/tag/v0.0.15),
[Windows repetition](https://learn.microsoft.com/en-us/windows/win32/taskschd/repetitionpattern),
[event subscriptions](https://learn.microsoft.com/en-us/windows/win32/taskschd/eventtrigger-subscription).

## Current-session startup fallback

The first installed 0.2.14 start revealed a Windows gap: a manually started task
returned failure without another observed restart, and its logon-bound repetition
had no next run in the current session. A simultaneous account shutdown also
triggered a conservative `unproven_orphan_frontend` refusal; subsequent inspection
found no remaining connector/frontend process. Unknown ownership remains a refusal,
not authority to terminate another account's process.

Version 0.2.15 separates a five-minute periodic trigger from the logon trigger.
Its first boundary is five minutes after registration, so it also covers the
current login session. IgnoreNew preserves a running supervisor. Disabled tasks
and durable stop intent still prevent launch. Resume and network events remain
additional quick startup triggers; no task wakes or reboots the workstation.

After the 0.2.14 controlled restart, both saved credentials received HTTP 401 with
`invalid_api_key` from an independent read-only request to the official OpenAI API.
The school's earlier successful polling does not establish current credential
validity. This is not attributed to a user key change or to the update. Both
connections require valid credentials for fresh host acceptance.

The final installed startup completed with a normal blocked-authentication state
for each unchanged rejected credential, with no remaining connector or frontend.
This is expected credential gating, not successful connectivity. A local credential
repair window was opened for the personal route. The user reported needing to
obtain a valid key, so no final selected-host call or disruptive OS event is claimed.
The required runtime permissions are [Tunnels Read + Use](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
