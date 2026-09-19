# Origin Companion 0.2.12 lifecycle candidate

Date: 19 September 2026. Baseline: 513ea6f (released runtime 0.2.11).
Status: **reviewed source, frozen package and controlled dual-account installation/readiness passed; draft PR remains a preview with separate CI, release and host/native/OS gates**.

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
| Full local pytest suite before the final fixture-only CI repair | **346 passed, 2 skipped, 93.88 seconds** |
| Lifecycle suite after atomic fixture publication | **40 passed, 61.94 seconds**; the failed duplicate-daemon scenario also passed five consecutive focused runs |
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
runtime's encoding was already explicit. A later Windows CI run also exposed a non-atomic write in the subprocess test fixture: termination during publication could leave an empty PID record, causing the next fixture command and teardown to fail. A deterministic write-interruption probe reproduced the old empty public file; atomic temporary-file publication leaves the public file absent. The fixture-only correction changes no shipped runtime files. [Draft PR checks](https://github.com/saigyujikingyo-png/origin-agent-bridge/pull/1/checks) track results for each exact revision; prior failures remain recorded.
Both local skips are Windows symbolic-link creation privilege limits. The Scheduler fixture does not establish installed rollback, actual logon or cloud account calls. Controlled installation/readiness evidence follows; those remaining outcomes stay unverified.

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

## Controlled installed acceptance

After independent review of runtime source `f83f1ca1` and package `b52e1bd8`, the
existing installation was upgraded using the checksum-verified packaged `integrate`
OpenAI route. The native self-test in `Install.ps1` was deliberately not invoked
under this acceptance scope. Both existing task registrations were read back with
unchanged startup preference; the previous 0.2.11 package remained intact and all
313 checksum-listed rollback files were verified. A backup is not an actual rollback.

Both configured accounts were explicitly started once and reached ready/healthy,
then produced later health observations. Independent official-client status and
process inspection found one daemon and one 0.2.12 MCP frontend per account, with
current executable and creation identities matching the configuration. No scientific
workflow was submitted. Queue/session records, scientific manifests, encrypted key
bytes, unrelated host configuration and the existing Claude/UoE process identities
were unchanged at readback. Cloud host calls remain a separate acceptance step.

The installer preserved profile bytes. The subsequent official-client connect
updated only `mcp.commands` to the installed 0.2.12 executable with the sole `serve`
argument. An initial strict pre-upgrade byte-equality assertion therefore failed;
that failure is retained. Read-only reconciliation verified every changed field,
the old and new executable paths, complete equality outside that command field,
unchanged tunnel identity/environment key reference and equal encrypted-key hashes.
The accepted result is **profile identity preserved with explicit engine-command
migration**, not byte-identical profiles after starting. No second install, restart
or rollback was performed to reconcile the observation.

## Open gates

- Passing CI for the revision selected for release, plus merge/public-release approval.
- Native self-check for this frozen candidate.
- Actual installed rollback and explicit stop/restart acceptance; initial explicit start and upgrade passed as described above.
- Fresh app/account connection, catalog and tool call for each intended host/account.
- Safe-window logon/reboot/network/sleep/logoff acceptance; no disruptive test was run.
- First-time vendor profile initialization and fresh-device credential setup.
- All previously unverified host/model/native/GUI/delivery combinations remain open.

The prior 0xC000013A termination source remains unknown. This repair demonstrates
specific lifecycle mechanisms; it does not prove the cause of that historical exit
or close the cross-product incident. Prior 0.2.11 scientific and two-account Work
passes remain historical. See [lifecycle record](origin-agent/docs/RUNTIME_LIFECYCLE.md).
