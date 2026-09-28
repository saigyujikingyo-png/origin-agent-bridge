# Connection reliability update design

Implementation update (2026-09-28): the candidate now implements isolated account state, pinned client packaging, identity-safe recovery and layered diagnostics. Real Windows client fixtures have exercised two-account cleanup and refusal/resume. The original investigation and proposed acceptance matrix below are retained as design history; each final acceptance result must be recorded separately. The legacy whole-map race has not been deterministically replayed.

Status: proposed for Origin Companion 0.2.13; implementation, package, installation and acceptance are pending.
Date: 2026-09-28. Accountable owner: the current Origin Companion Product Max.
Baseline: Origin Companion 0.2.12, source b717e598b2d34520122d146942d3c826455e517c.
The installed executable records frozen source f83f1ca1b1cb68917f7ec55c6364d005cc153f2a.
This document is a repair specification, not a release certificate.

## Problem and evidence

A remote Origin call can fail with `tunnel_client_not_seen` while a different account
still has a live local tunnel and MCP frontend. Local health, process ownership,
vendor registration, supervisor health and the host's selected account are separate
observations. An idle Task Scheduler task is not a healthy connection.

Read-only inspection found a missing runtime for the failing route. Another managed
account had a live daemon/frontend chain, but its vendor process registry pointed to
an older daemon. The vendor history recorded the new daemon's successful launch.
Both account supervisors had exited with a durable `reconciliation_failed` state.

| Finding | Evidence strength | Implication |
| --- | --- | --- |
| The failing route has no live owned tunnel | Current host error plus independent OS scan | The mini-project cannot presently make a fresh Origin call |
| A different account has a live daemon but an old registry PID | Current process identity, launch history, local health and registry comparison | Repeatedly reading the registry cannot prove the actual daemon is stopped |
| tunnel-client 0.0.14 rewrites shared whole-map state without a transaction lock | Official source inspection | Concurrent aliases can overwrite one another's records; a common fixed temporary filename adds another collision risk |
| A lost update explains the observed registry regression | Strong inference from old registry/new launch history and overlapping starts | Exact overwriting process and interleaving have not been captured; do not call the race reproduced on this machine |
| Cleanup failure discards the original cause in durable state | Current source plus isolated fault injection | Historical `reconciliation_failed` alone cannot identify the failing cleanup operation |
| Non-ready records do not receive the freshness check applied to ready records | Current source plus isolated fault injection | Diagnostics can present an old failure without establishing current supervision |
| A probe timeout enters generic cleanup | Current source plus isolated fault injection | Temporary diagnostic/network problems can trigger disruptive connector recovery |
| Logon tasks can exhaust their finite restart budget | Existing configuration and lifecycle contract | A later network recovery does not guarantee a new supervisor start |

DNS errors, aborted sockets and control-plane poll timeouts were observed. They are
not proof of bad credentials, a firewall defect, or an Origin native failure.
There was no fresh scientific job associated with the blocked continuation.

The precise historical cleanup exception, the termination source of the older
0xC000013A incidents, and the causal effect of simultaneous admission remain unknown.
The shared incident stays open.

## Upstream dependency decision

Use an explicitly pinned and verified tunnel-client 0.0.15 candidate, subject to
Windows compatibility and process-ownership tests. It was released on 2026-09-25.
Its state lock covers the read/launch/persist transaction and its process records
include additional identity checks.

Upgrading Origin alone while sharing the old global state directory is insufficient:
older clients used by other products do not participate in the new lock. Therefore
state isolation and the dependency update must be evaluated together.

Release metadata currently reports this Windows AMD64 archive:

- Artifact: `tunnel-client-v0.0.15-windows-amd64.zip`
- SHA-256: `3b53133a1e24d43f63088d843860cb1701a4c3ed6390de2e19f69089e43bddc1`
- This is published metadata, not a locally downloaded or verified artifact.
- Verify the downloaded bytes against the pinned checksum before extraction; record
  archive, executable, licence and provenance separately. Never resolve “latest”
  during a user's startup.

## P0: Isolate vendor state by managed connection

Add a versioned `client_state_dir` to each managed connection configuration, with
the canonical location derived from that connection's private cloud root, for
example `<connection-root>/tunnel-state`. Validate containment, canonical scope,
and conflicting/symlinked paths according to the existing ownership rules. An
arbitrary path from inherited environment must never select the state root.

Set `TUNNEL_CLIENT_STATE_DIR` explicitly in the child environment for every vendor
connect, status and diagnostic invocation. The daemon must inherit the identical
value. Do not change the machine or user's global environment. Separate Origin
accounts receive separate roots; the shared Origin scientific device lock and job
database remain shared.

Configuration version 2 must distinguish a legacy connection from a migrated one.
Do not silently let a schema-1 launcher ignore the field and return to global state.
There must be no unattended migration inside a status call or ordinary startup.

A connection generation should bind the canonical scope, configuration version,
client state root and chosen executable identity. Adoption must verify that binding
as well as the existing OS user, executable, command, PID, creation time and recorded
lineage. A daemon started against a different state root is not automatically adopted.

Retain independent OS enumeration. The vendor registry is evidence, never authority
to kill a process. A stale registry must not weaken the existing identity checks.

## P0: Preserve failure causes and report fresh local state

Persist a small, versioned diagnostic envelope:

- Current state and observation timestamp/expiry.
- Scope/generation identifier, supervisor alive/absent/unknown, and process identity
  match/mismatch/unknown.
- Primary failure code and phase, plus a separate cleanup failure code and phase.
- Local MCP health, vendor registry consistency, and control-plane observation,
  each with its own timestamp and evidence source.
- Attempt count, retry budget, next retry time, and an actionable recovery category.

Use allowlisted error codes and sanitized exception classes. Do not serialize raw
stderr, exception text, keys, signed URLs, profile contents or arbitrary command
arguments. Retain the last event and a bounded private transition history with
monotonic sequence numbers, atomic publication and fixed rotation limits.

Preserve the historical state as history while deriving freshness and supervisor
liveness for every current response. A stopped or authentication-blocked intent
does not become an instruction to restart merely because its observation is old.
Local state must remain inspectable when the remote connector is unreachable.

Report a sanitized startup failure even when validation, admission, DPAPI loading
or engine selection fails before Controller construction. If scope cannot be
validated, emit a local launcher diagnostic without writing into an untrusted path.

Existing MCP output schemas remain meaningful and server-validated. Any diagnostic
fields exposed by tools need compact schema coverage and compatibility tests.
Do not add a large new tool catalogue just for recovery.

## P0: Distinguish transient failure from ownership failure

Keep one long-lived supervisor per connection and bounded commands. Preserve the
vendor daemon during a transient failure when its exact identity and scope remain
proven. A proposed state policy is:

| Situation | State and action |
| --- | --- |
| Exact owner, coherent registry, local health confirmed | Locally ready; remote reachability remains separately evidenced |
| Same owner but a transient status timeout or poll/network error | Degraded; invalidate successful reachability, preserve owner, use bounded observation retries |
| Same owner with inconsistent registry | Registration conflict; preserve the owner and capture diagnostics, do not spawn a replacement |
| Owner confirmed absent | Reconcile remaining proven frontend ownership, then allow one bounded connect attempt |
| Unknown/orphaned owner or incomplete cleanup | Recovery blocked; no new connect until explicit reconciliation succeeds |
| Authentication rejection established by a reliable error | Authentication blocked; no retry storm or automatic key rotation |
| Manual stop or installation fence | Stop/maintenance policy; no autonomous restart |

Allow a short observation grace period before connector replacement; tune it using
fault-injection results, not an unbounded increase in timeouts. Local HTTP success
must never imply a recent control-plane connection or successful host call.
If the official client cannot expose a reliable recent poll observation without
extra privileges, report that layer as unknown rather than infer it from logs or
require a new admin credential.

For prolonged network failure, keep a low-frequency bounded retry loop within the
existing supervisor, proposed delays 30, 60, 120 and then 300 seconds with jitter.
This is observation/reconnect policy, not permission to replay scientific work.
Reconnection requires proven absence or completed reconciliation. Ownership,
authentication, manual-stop and maintenance states do not use this network loop.

Use existing stop signals and installation fencing to interrupt waits promptly.
Do not create a second watchdog service. Retain a bounded scheduler restart policy
for an actual supervisor crash, with a durable reason visible if that budget is
exhausted. A disabled/manual-stop preference must survive every path.

## P1: Handle startup contention without concealing installation state

The administrative admission gate is currently nonblocking. Simultaneous account
logon can contend even though the long-lived connection locks are separate.

Introduce a short bounded wait only for harmless startup contention, reloading
configuration and intent under the gate. An installation transaction marker, invalid
scope, explicit stop, or engine mismatch still refuses startup immediately with
a durable reason. The administrative lock must be released before supervision.
Keep lock ordering explicit: administrative admission, then connection ownership;
never hold admission while waiting for shutdown of a supervisor.

This is a confirmed unhandled contention path, not a confirmed cause of this incident.

## Transactional migration and rollback

Implement through the existing installation journal and lifecycle fence:

1. Discover supported Origin scopes. Validate all paths and exact task ownership.
   Snapshot configuration/profile hashes, installation pointer, task definitions,
   enabled/disabled intent and connection generations. Do not read/export credentials.
2. Acquire the administrative fence and disable only proven Origin registrations.
   Quiesce each affected connector using existing identity and lineage rules. If
   cleanup remains unknown, abort before switching the installation pointer.
3. Stage the verified client, runner and schema-2 configurations with empty private
   vendor state roots. Preserve existing tunnel IDs, alias/profile identities,
   secret references, scientific jobs, output hashes and user stop intent.
4. Do not copy the whole shared registry into the new roots. Re-register the same
   existing tunnel through the supported vendor path during an explicit controlled
   start. Do not create new remote tunnels or rotate keys.
5. Publish the coherent configuration/runner/engine transaction, then restore task
   policy only after verified file and receipt readback. Reinstallation alone does
   not authorize starting previously disabled connections.
6. Leave other products and the legacy shared registry intact. Obsolete Origin
   records there are not evidence of the new connection. Prevent old managed
   launchers from consuming the new configuration silently.
7. Rollback first quiesces the exact new generation, restores the complete previous
   lifecycle configuration and pointer, and verifies intent/task restoration.
   If an old release resumes global state, report the old reliability risk; a
   successful file rollback is not proof of repaired connectivity. An uncertain
   rollback keeps the transaction fence and recovery receipt.

No process-tree kill, credential reset, registry deletion or unrelated plugin upgrade
is part of this repair. A source patch must not silently modify an installed runtime.

## Implementation work packages

| Priority | Source areas | Required result |
| --- | --- | --- |
| P0 | `tunnel_lifecycle.py`: Connection, command environment, scan/probe/adoption | Validated state root and generation; all commands agree on scope |
| P0 | `tunnel_install.py`, `installation.py`, install/runner scripts | Pinned dependency, schema migration, journaled state-root change and rollback |
| P0 | `tunnel_lifecycle.py`: note, status, supervise; runner | Fresh layered diagnostics, retained primary/cleanup causes and early startup failures |
| P0 | `tunnel_lifecycle.py`: recovery policy | Transient degradation preserves exact owners; uncertainty blocks spawning |
| P1 | `lifecycle_admission.py`, run/start entrypoints | Bounded startup contention with unchanged maintenance and stop semantics |
| P1 | Diagnostic presentation and documentation | Simple account-specific status and recovery action, available locally while offline |
| P0 | Lifecycle/install/admission tests and real-client harness | Evidence below, with process cleanup receipts and no native scientific calls |

## Acceptance matrix

These are required future checks, not reported passes.

| Gate | Scenario | Pass condition |
| --- | --- | --- |
| A: vendor compatibility | Verified 0.0.15 with loopback-only fake control plane/MCP | JSON contracts, environment inheritance and exact process identity understood; no real account used |
| B: shared-state regression | Two synchronized aliases against 0.0.14 in a disposable root | Demonstrate and preserve the lost-update interleaving; report failure to reproduce honestly |
| C: isolation | Two Origin scopes plus a simulated old client writing its own legacy root | Both scoped registrations/health remain correct; legacy state untouched by Origin |
| D: transient faults | Delayed status, DNS/poll failure, socket interruption, outage longer than old retry budget | At most one daemon/frontend chain per scope; no churn during observation grace; bounded recovery after connectivity returns |
| E: refusal paths | Authentication, stale/PID-reused registry, unknown orphan, cleanup refusal | Correct layered diagnostic; no new daemon, no unrelated process action |
| F: interruption | Abrupt supervisor exit, cancellation and stop during each retry phase | Next start adopts/reconciles exactly; manual stop persists; all waits are interruptible |
| G: migration | Personal plus school, one disabled, competing starts, injected crash at each publication phase | Complete rollback or fenced recovery; no lost intent, jobs, profile identity or secrets |
| H: real Windows cleanup | Isolated actual Go client and frontend, multiple threads, stale registry | Exact producer quiescence/exit observed; refusal resumes preserved owners; no Python-only substitute for this gate |
| I: diagnostics | Primary+cleanup errors, old non-ready records, pre-controller failures | Correct cause chain/freshness, compact validated schema, zero secret/raw-log leakage |
| J: package | Build from reviewed source; archive/executable manifests | Exact provenance and licence/checksum verification; portable tests and Windows fixture tests recorded separately |
| K: installed account routes | Each intended host/account with read-only calls after controlled activation | Host-selected identity proven; repeated fresh calls succeed; local health alone never passes this gate |
| L: workstation lifecycle | Safe logon/sleep/wake/network/logoff window | Observed state and recovery match policy; no automatic disruptive workstation test |
| M: science and delivery | Explicitly authorized bounded scientific task after K | Fresh native artifact and hash/readback, scientific result and host delivery recorded separately |

Retain existing PID-reuse, saved orphan, unknown orphan, duplicate producer,
manual-stop, installation fence and rollback regression coverage. Test the complete
candidate rather than only a proposed fast path. Full native/host acceptance does
not follow from the isolated fault probes used to diagnose this incident.

Release/installation remains subject to the applicable shared lifecycle contract
review and a concrete product-owned technical acceptance receipt. Shared-principles
governance is not delegated product debugging. No existing shared incident is closed
by approving this design.

## Evidence gathered in this investigation

Three isolated in-process fault injections executed against the baseline source:

1. A simulated readiness error followed by simulated cleanup refusal left only
   `reconciliation_failed` as the final durable reason, while the cleanup exception
   propagated. This verifies cause masking, not the historic cleanup exception.
2. An expired non-ready record with no supervisor was returned unchanged by status.
3. A simulated command timeout after readiness invoked cleanup immediately.

No live connector was restarted, installed or terminated for these probes.
No fresh Origin science was run. The legacy vendor race has not been deterministically replayed. Repaired behavior is now exercised separately by the opt-in real-client Windows fixture; this does not turn the historical incident inference into a proven cause.

## Primary references

- [Official v0.0.14 manager](https://github.com/openai/tunnel-client/blob/v0.0.14/pkg/codexplugin/manager.go): Connect reads whole-map state before launch and saves it afterward.
- [Official v0.0.14 state storage](https://github.com/openai/tunnel-client/blob/v0.0.14/pkg/codexplugin/state/state.go): root override and whole-map persistence.
- [Official v0.0.15 state lock](https://github.com/openai/tunnel-client/blob/v0.0.15/pkg/codexplugin/state/lock.go): transaction lock shared by aliases.
- [Official v0.0.15 manager](https://github.com/openai/tunnel-client/blob/v0.0.15/pkg/codexplugin/manager.go): locked connect transaction.
- [Official v0.0.15 release](https://github.com/openai/tunnel-client/releases/tag/v0.0.15).
- [Official secure MCP tunnels guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
- Product baseline: `tunnel_lifecycle.py`, `tunnel_install.py`,
  `lifecycle_admission.py`, runner scripts and `docs/RUNTIME_LIFECYCLE.md`.
