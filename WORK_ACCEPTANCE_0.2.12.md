# Origin Companion 0.2.12 lifecycle candidate

Date: 19 September 2026. Baseline: 513ea6f (released runtime 0.2.11).
Status: **source and isolated package checks passed; draft PR opened; amended candidate review, installation and host gates remain pending**.

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
| Ruff check and format | Passed; 98 Python files formatted |
| Full pytest suite | **346 passed, 2 skipped, 93.88 seconds** |
| Installation and admission focused suite before the Scheduler JSON correction | **82 passed, 1 skipped, 11.84 seconds**; the full suite above includes the corrected adapter |
| Focused connector lifecycle suite after alias-absence fix | **38 passed, 58.24 seconds** |
| Independent review of alias-absence fix | Passed; 9 separately exercised in-memory cases, including marker spoofing and cleanup refusal |
| Independent final transaction review | Passed after fixing each reproduced race; 16 recovery cases plus the original wrong-receipt activation reproduction independently rechecked |
| Actual CLI version and lifecycle subcommands | 0.2.12; run/status/stop/startup/initialize routes available |
| Existing account/task discovery | Both configured accounts matched exactly one owned registration; read-only, no changes |
| Real Windows Scheduler adapter | Passed: uniquely named current-user harmless task registration, readback, disable, XML restoration and exact cleanup; no command executed |
| Real PowerShell/DPAPI fixture | Passed with dummy secret, Unicode path, inherited PowerShell 7 module paths, no key in argv/output, scoped state restored |
| Frozen Windows review candidate | Built; 315 package files verified against SHA-256 inventory; frozen source hashes match; executable reports 0.2.12 |
| Frozen MCP protocol and output contracts | Passed in auto/legacy transports and economy/full profiles; 5/14 advertised schemas, status, compatible text and economy help checked in isolated state |

The rebuilt unpublished ZIP/MCPB candidate is 33,196,535 bytes (31.66 MiB). Both have
SHA-256 `b52e1bd8adeb17f5bdd760b56203d367f5ee05c7880c44ea93b63a880cbb75da`.
Earlier candidates are withdrawn. The `edbbbdf5` candidate passed source review
but failed the actual Windows Scheduler prerequisite before any registration:
Windows PowerShell 5.1 emitted empty output for a null result. The corrected driver
writes explicit JSON null for absent tasks and successful void operations; malformed
or missing unexpected output still fails parsing. A real read-only regression
failed before the change and passes now. The disposable task completed all steps,
restored identical exported XML and was removed after exact ownership verification.

Initial GitHub Windows CI also exposed fixture reads that relied on the system
encoding for generated UTF-8 configuration. Test readers now specify UTF-8; the
runtime's encoding was already explicit. Subsequent CI is a separate gate.
Both local skips are Windows symbolic-link creation privilege limits. Installed
account migration/rollback, actual logon and cloud account calls remain unverified
for this candidate. The Scheduler fixture does not establish those outcomes.

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

Administrative admission now blocks starts during publication, pointer changes
and rollback. An exact replay of the governance race rejects the concurrent start
and restores the original 0.2.11 pointer, startup preference and absent intent file.
Cross-process tests cover competing transactions, abrupt owner death and matching
receipt recovery; configuration rebinding and a stale frozen executable are refused.

Planned stop bytes are journalled before publication. Tests interrupt installation
and repeated recovery before/after that write, after preference restoration and
before final receipt commit. Exact original/previous/planned hashes distinguish the
transaction's writes from a later manual stop. Legacy task definitions stay disabled
until rollback commits; pending activation is resumed by readback without repeating
shutdown or native work. Wrong recovery receipts cannot acquire a fence that would
block the matching activation. Live legacy command children refuse upgrade quiescence
and the preserved wrapper is resumed. Windows console-host helpers are identified
by their exact system executable path.

A read-only query to the installed official tunnel client 0.0.14 established its
never-registered-alias diagnostic. Only exit 1 with that exact diagnostic for the
requested alias permits initial connection, after ownership reconciliation. This
uses the existing validated tunnel identity; it does not create or rotate one.
Other exit codes, extra diagnostics, authentication errors, bad JSON, conflicting
profiles/directories and a reserved absence marker supplied in successful JSON
are rejected. The 11 rejection cases prove that none starts a connection.

## Open gates

- Independent review of the amended Scheduler fix and package before installation or release.
- Published CI and native self-check for this frozen candidate.
- Actual installed dual-account upgrade, registration readback, stop/start and rollback.
- Fresh app/account connection, catalog and tool call for each intended host/account.
- Safe-window logon/reboot/network/sleep/logoff acceptance; no disruptive test was run.
- First-time vendor profile initialization and fresh-device credential setup.
- All previously unverified host/model/native/GUI/delivery combinations remain open.

The prior 0xC000013A termination source remains unknown. This repair demonstrates
specific lifecycle mechanisms; it does not prove the cause of that historical exit
or close the cross-product incident. Prior 0.2.11 scientific and two-account Work
passes remain historical. See [lifecycle record](origin-agent/docs/RUNTIME_LIFECYCLE.md).
