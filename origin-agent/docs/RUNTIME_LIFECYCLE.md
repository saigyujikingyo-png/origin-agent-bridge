# Origin runtime lifecycle

Record version: 1.0. Shared rules: 2026-09-19.1, lifecycle contract 1.0.
Implementation candidate: 0.2.12, the runtime-lifecycle change after source 513ea6f.
**Not yet a released or installed acceptance certificate.**

## Component ownership

| Component | Lifetime and owner | Scope |
| --- | --- | --- |
| Remote connector | Persistent while the Windows user is logged in; an optional limited interactive logon task starts a thin PowerShell DPAPI adapter and the installed Python supervisor | OS user + canonical profile directory + profile; one daemon and one logical MCP frontend chain |
| Local MCP frontend | Host starts it and owns stdio/EOF; no task or autostart required | Claude, WorkBuddy, Codex or another host can each own frontends |
| Scientific scheduler | Existing device/scheduler locks serialize the shared Origin executor; accepted job IDs and SQLite records are independent of a tunnel retry | Per Windows state root/device; not per remote account |
| Native/session worker | Existing PID/creation-time fencing and session revisions apply; unsaved or unowned native applications are preserved | Explicit Origin/session/job ownership |

Personal and school connections have separate alias/profile directories and secret
references. They intentionally share the user's Origin data and single execution
device; this is not a multi-tenant security boundary. No connection restart submits
a scientific workflow, replays an uncertain operation, deletes outputs, or rotates a key.

## Connection state machine

The release-owned controller is `src/origin_agent/tunnel_lifecycle.py`. The Windows
runner reads a parameterized `runtime-config.json`, loads the existing DPAPI secret
into the child environment and invokes the installed engine. Secrets never appear in
process arguments, source, receipts or error text. The supervisor uses existing
Python/psutil dependencies; no extra service, database or model provider is added.

Before any spawn-capable connect, the controller persists attempt intent. It scans
the OS independently of the vendor alias registry, validates the alias metadata,
and either adopts the same healthy/starting owner or reconciles proven old owners.
Every connect/status command has a 20-second timeout. Initial readiness polls the
same owner for at most 90 seconds; continued health is checked every 15 seconds.
The success observation expires after 40 seconds and is invalidated on probe failure.
The public diagnostic also checks its supervisor identity. A cached observation is
not a fresh remote call or proof of app/account binding.

States include absent, spawning, starting, ready, unhealthy, stopping, stopped,
failed, stale and unknown. State files contain observation time, expiry, canonical
scope and process identities. Legacy background-status readers receive the same
invalidated state instead of an old permanent success flag.

Failures use bounded delays of 5, 15 and 30 seconds. Five minutes of observed health
resets this budget. Authentication failure stops the sequence. Each retry first
reconciles the attempt, including daemons missing from registry metadata. An
ownership conflict or unconfirmed cleanup stops recovery without spawning again.
Task Scheduler may restart a failed supervisor at most three times at one-minute
intervals. A prolonged outage can exhaust both budgets; explicit start is the
recovery route after the underlying problem is resolved.

## Process fencing and explicit stop

A daemon is identified by the actual executable, exact command profile/directory,
OS user, PID and creation time. The registry start time must agree with the OS
observation. MCP lineage is recorded while its parent identity is observable;
previously recorded children can then be reconciled after their parent exits.
An orphan without this proof is preserved and blocks a new attempt. PID-only,
basename-only and stale-parent-PID cleanup are forbidden.

During cleanup, proven connector producers are briefly suspended before their
children are enumerated, closing the spawn-during-termination race. Only the proven
daemon and its `serve` frontend chain are terminated. Native applications, accepted
job supervisors and unrelated hosts are neither suspended nor killed. A refused
cleanup resumes any preserved producer. All destructive actions recheck identity.

The profile lock is beside the canonical profile, so alternate paths to the same
configuration cannot start a second supervisor. Separate profiles use separate
locks. Managed entrypoints share this lock; conflicting external launchers are
detected by OS enumeration and fail-closed reconciliation.

Explicit stop writes a durable stop intent before waiting for the supervisor to
exit cooperatively. A stale legacy wrapper has no cooperative protocol; it can be
stopped only with current-user, executable, exact script path and PID/start proof.
No Task Scheduler process-tree kill is used. A disabled/manual-stop preference
survives reinstall. Only an explicit start clears it.

A legacy PowerShell wrapper is suspended before its children are inspected. If a
live command remains below it, shutdown refuses and resumes the wrapper instead of
orphaning a command that could spawn later. Only the exact Windows system console
host is excluded from that producer check. Retry the upgrade after the legacy
command ends; an unresolved command is not permission to kill a whole process tree.

## Installation, upgrade and rollback

`tunnel_install.py` discovers the personal profile and supported account folders,
renders the same versioned configuration/launcher, and preserves existing tunnel
identities, key references and profile bytes. Ambiguous profiles, task ownership or
paths fail before the installation pointer is switched. There is no account-name
replacement or private account ID embedded in the release.

Upgrade disables only proven registrations temporarily, quiesces their connector
owners, then updates launcher/configuration and the installation pointer. It retains
file/task backups and enabled/disabled/manual-stop intent. It does not restart
connections automatically during reinstall. Rollback covers lifecycle files and
registrations as well as the previous engine pointer, subject to conflict checks.
Outputs, jobs, credentials and licences remain local and unchanged.

`lifecycle_admission.py` adds one administrative lock per canonical state root,
separate from the long-lived runtime profile lock. Installation, startup setup and
rollback hold this lock through shared-state changes. Public start and profile
initialization must enter the same gate. A runtime acquires its profile lock while
admitted, then releases the administrative lock before supervision so shutdown
cannot deadlock. It reloads the installation pointer under the gate and rejects a
configuration rebound to another state root or a frozen executable selected before
the pointer changed.

A receipt-linked transaction marker survives abrupt installer death. Ordinary
start/reinstall refuses that partial state. Explicit rollback with the matching
receipt is the recovery route; a failed rollback does not clear the marker merely
because the original receipt still says `installed`. Successful completion or a
verified rollback clears it. A malformed marker or edited configuration remains a
reconciliation issue, never an automatic overwrite.

Intent updates have a short separate lock and exact before/after digests. Installer
shutdown journals its planned stop write before publishing it, then releases the
intent lock before waiting for process shutdown. A later user stop is not adopted
as the installer's own write or overwritten by restoration. Recovery covers a
crash during stop as well as during launcher, pointer and receipt publication.
When rolling back to an older launcher, task activation follows complete file and
receipt restoration; task-request acceptance is still separate from runtime health.

Uninstalling an account registration removes no cloud account or research data.
Use the explicit stop route before removing its owned task; an unrelated registration
or process must be left intact. Full automatic product removal is not newly claimed.

## OS events and evidence gates

Startup is **user logon**, not machine boot before login. A normal conversation
ending does not intentionally stop the remote connection. A killed supervisor
invalidates observed health; the next authorized start reconciles/adopts surviving
owners. Persisted jobs are not a promise of uninterrupted execution through host
termination, user logout, shutdown or power loss.

| Gate | Evidence and boundary |
| --- | --- |
| Delayed readiness and command failures | Isolated real-process fixtures exercise delayed-ready, before/after-spawn failure, status failure/hang, command deadline and absent child |
| Ownership and retry | Real fixtures inspect daemons/children at retry boundaries, adoption, duplicate cleanup, missing registry, orphan proof, PID creation mismatch and two profiles |
| Stop and supervisor loss | Cross-process lock, abrupt supervisor death/adoption, cooperative stop and persistent manual-stop intent fixtures |
| Installation transaction | Real filesystem and isolated-process tests: multi-account, disabled, competing starts/installs, crash fence, matching recovery, partial publication and rollback; real scheduler acceptance remains separate |
| Native scientific regressions | Historical 0.2.11 evidence remains historical; no science change is intended by this patch |
| Packaged/install/current-device | Pending independent governance review and installation of the candidate |
| Remote app/account/catalog/call | Independent per-account governance acceptance; local health is insufficient |
| Actual logon/reboot/sleep/network/logoff | Unverified for this candidate; requires a safe workstation window, never an automatic disruptive test |

The September 2026 `0xC000013A` exits have no established termination source.
Retry/readiness defects are independently confirmed; fixing them does not prove
the historical exit's cause or close the shared incident. Published output contract
1.0.0 and scientific/host/artifact-delivery acceptance remain separate.
