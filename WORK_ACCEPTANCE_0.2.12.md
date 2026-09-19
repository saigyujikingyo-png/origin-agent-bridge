# Origin Companion 0.2.12 lifecycle candidate

Date: 19 September 2026. Baseline: 513ea6f (released runtime 0.2.11).
Status: **source verification passed; publication/installation and host gates pending review**.

## Change and invariants

The old runner checked readiness once and retried without reconciling a daemon
that may already have started. Its success receipt could remain ready indefinitely.
The candidate polls a single owner with deadlines, checks ongoing health, invalidates
stale results and reconciles proven owners before retrying. Unknown ownership blocks
a new attempt. All supported launcher paths use the same canonical profile lock.

Personal and additional account profiles now use one release-owned configuration
generator. Upgrade/rollback preserve identities, encrypted credentials, enabled or
manually stopped preferences and unrelated host/native/job processes. Installation
quiesces connectors before switching the engine and does not explicitly restart them.
Scientific workflows and output contract 1.0.0 are unchanged.

## Fresh source checks

Windows x64, Python 3.12.14, locked environment:

| Check | Result |
| --- | --- |
| Locked offline dependency sync | Passed; project version updated to 0.2.12, no new runtime dependency |
| Ruff check and format | Passed; 96 Python files formatted |
| Full pytest suite | **281 passed, 2 skipped, 82.20 seconds** |
| Actual CLI version and lifecycle subcommands | 0.2.12; run/status/stop/startup/initialize routes available |
| Existing account/task discovery | Both configured accounts matched exactly one owned registration; read-only, no changes |
| Real PowerShell/DPAPI fixture | Passed with dummy secret, Unicode path, inherited PowerShell 7 module paths, no key in argv/output, scoped state restored |

Both skips are Windows symbolic-link creation privilege limits. Linux execution
of the candidate remains a CI gate. The real Windows Task Scheduler adapter was
read, but task creation/migration/rollback has not yet been exercised on installed
registrations. A fixture is not acceptance of an actual logon or cloud account.

## Failure-path coverage

Real isolated subprocess fixtures cover delayed readiness, failure before/after
spawn, connect/status timeout, readiness timeout, absent MCP child, post-start
status failure, retry cardinality, healthy owner adoption, duplicate scoped daemons,
missing registry, saved-lineage orphans, unknown orphan refusal, two profiles,
unrelated frontend and simulated durable-job process preservation, PID creation mismatch, stale success,
manual stop, cross-process singleton, supervisor death/adoption and cooperative stop.

Cleanup-refusal tests confirm preserved producers are resumed; one failed resume
does not prevent attempts for the others. Readiness rechecks child liveness and
parent creation identity after the status probe. Producer suspension closes a
spawn-during-cleanup race. POSIX stopped-process termination uses hard termination;
unreaped zombies are not counted as live owners. Linux CI must verify these paths.

Filesystem/task-boundary tests cover personal/additional account migration,
reinstall, explicit startup, disabled and manual-stop persistence, ambiguous tasks,
extra actions, profile/key-reference refusal, quiesce/write/registration failure,
publication-before-pointer rollback, changed-file/task conflicts and preservation
of current stop preferences during a completed-install rollback. New profile
initialization is locked, bounded, validated and refuses existing identities.

## Open gates

- Independent governance review before publication or installation.
- Published CI, frozen package/checksum/size and native self-check for this candidate.
- Actual installed dual-account upgrade, registration readback, stop/start and rollback.
- Fresh app/account connection, catalog and tool call for each intended host/account.
- Safe-window logon/reboot/network/sleep/logoff acceptance; no disruptive test was run.
- First-time vendor profile initialization and fresh-device credential setup.
- All previously unverified host/model/native/GUI/delivery combinations remain open.

The prior 0xC000013A termination source remains unknown. This repair demonstrates
specific lifecycle mechanisms; it does not prove the cause of that historical exit
or close the cross-product incident. Prior 0.2.11 scientific and two-account Work
passes remain historical. See [lifecycle record](origin-agent/docs/RUNTIME_LIFECYCLE.md).
