# Implementation design for the specified Origin builds

Target: a personal sharing plugin for students and staff using standard Origin 2026 SR1 (10.300197) or 2026b SR2 (10.350243), Windows x64. Users describe scientific/editing goals; the agent discovers, executes and verifies operations without requiring script expertise or manual connection JSON. Record each build's acceptance separately; see the [current report](../../WORK_ACCEPTANCE_0.2.8.md).

Codex is the development and maintenance environment. Runtime callers are cloud/local Work, Claude Desktop, WorkBuddy and other general agents. Execution is independent of a source directory, development terminal, code project and development-task lifetime.

## Processes and modules

```text
Cloud Work / Local Work / Claude Desktop / WorkBuddy / other agents
                 | MCP: local stdio or supported cloud connection
                 v
server.py ---- capabilities.py: on-demand discovery and documentation
   |
   +-- fixed workflows / independent programs: snapshots, plans, artifacts
   +-- sessions.py: request_id / expected_revision operations
                 |
                 v
jobs.py: shared SQLite queue, device lock, timeout, cancellation, deduplication
                 | atomic local-file mailbox; no extra network service
                 v
session_native.py: single-thread worker -> one managed Origin instance
   +-- program_native.py: Python / LabTalk / X-Functions / Origin C
   +-- gui.py / gui_session.py: observations and GUI transactions
   +-- gui_native.py / gui_accessibility.py: managed-PID Win32/UIA adapters
   +-- checkpoints, read-back, previews and recovery
```

The MCP process does not import Origin COM. Native calls run serially on the worker's main thread. Sessions reuse that worker; hidden idle sessions save/exit, visible sessions remain for manual work, and checkpoints support later restoration. Independent jobs remain available and use the same device queue.

The local mailbox reuses existing atomic storage and queue infrastructure, avoiding extra HTTP servers, ports, token distribution, database services or inference calls. Packages retain one Python stack. Candidate knowledge/object/session designs are reused only after relevant tests; failed analysis wrappers do not enter default paths.

## Session consistency

- `origin_session` opens, inspects, checkpoints, restores and closes, returning existing job IDs for control operations.
- `origin_run_program` adds optional `session_id`/`expected_revision`; omission retains independent execution.
- Reuse `origin_get_job` and `origin_get_artifact` rather than creating another task/file protocol.
- A stable `request_id` returns the same job on retry; reusing it with different content is rejected.
- Mutations carry the latest `expected_revision`, checked before writing. Success advances the revision.
- New sessions create managed Origin or load a selected project copy. Manual changes in that instance enter later checkpoints. Do not automatically take over unrelated unsaved windows.
- Save an immutable pre-change OPJU checkpoint; restore it on program failure. Recovery does not undo external file/network side effects.
- Do not reopen a live project merely to verify each edit. Distinguish saving/read-back from reopening; use a separate validation job when needed.

## GUI and coverage

Observe managed windows/dialogs/controls, act on a unique target, then observe again. Prefer native controls/UIA; ambiguous targets or blocking dialogs return diagnostic states rather than blind repeated clicks. Screenshots support graph review and custom controls. GUI requests use the same queue, revisions and checkpoints.

Categorise imports, sheets/matrices, 2D/3D/statistical graphs, graph details, fitting, statistics, signals/peaks, templates, Apps and projects/exports. Record discovery, execution and result verification separately. The agent loads relevant parameters/examples on demand, combines related operations and returns small summaries and artifact IDs.

## Installation and implementation sequence

Continue with frozen ZIP/MCPB packages: verify files, detect target Origin, generate local paths, preserve/merge host configuration and perform a synthetic native self-test before completing the active installation switch. Supply a natural-language example. Users keep their own accounts/licences; cloud access uses supported personal connections, without packaged developer keys or an extra paid model layer.

1. Persistent sessions: same PID, checkpoint/error/cancellation recovery, stale edits, cross-MCP continuation and idle wake-up.
2. GUI observation/actions: target PID only, modal recognition/dismissal, menu/control evidence, blocking and bad-target tests.
3. Sharing packages: no external Python/JSON work, configuration/rollback, non-ASCII and user paths, offline runtime and real host/model checks.
4. Category coverage: native numbers, figures and editability for real research cases; convert failures into reproducible regressions.

Measure cold startup, continued-edit time, calls, response size, memory and recovery. There is no established universal coverage or billed-token reduction percentage. A narrow build baseline and compact interfaces reduce compatibility/context work; session state, Origin resource use, custom controls and scientific judgement remain costs.

## Implemented milestones

Persistent sessions, Win32/UIA/screenshot input, configuration backup/rollback and native installation self-tests are implemented. Frozen 0.2 acceptance covered fixed workflows, general programs, 24 session jobs and 43 GUI jobs. See [GUI.md](GUI.md), [VALIDATION.md](VALIDATION.md) and `origin_capabilities("coverage")`. Broad mechanisms do not certify every function, device or host model. Branding is Origin Companion with a blue open-circle icon.

From 0.2.1, `agent_profiles.py` provides full/economy modes on the existing MCP server, with no provider client or second native core. Public `list_tools/call_tool` paths retrieve/validate arguments on demand. Recipes reuse Workflow/plan/submit and existing deduplication, revision and GUI constraints. `configure-model` saves a local profile with CLI/environment overrides; keys remain in the host. `benchmark_profiles.py` measures schema bytes and `verify_economy.py` checks native execution/pagination; real model quality needs separate evidence.
