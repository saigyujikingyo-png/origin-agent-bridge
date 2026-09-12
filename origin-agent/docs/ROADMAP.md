# Roadmap and acceptance gates

Scope: personal sharing with classmates and staff using licensed Origin 2026 SR1 (10.300197) or 2026b SR2 (10.350243), Windows x64, standard edition. Each person uses their own Origin licence and agent account. Mark capabilities passed only with actual evidence. Current device/host results are in the [0.2.8 report](../../WORK_ACCEPTANCE_0.2.8.md); the stages below preserve their original test scope.

| Stage | User capability | Gate | Recorded status |
| --- | --- | --- | --- |
| 0: version and native execution | Exact build detection, local discovery, Python/LabTalk/Origin C, editable OPJU | Numerical fits, reopen, exports, unsupported-version rejection | Recorded cases passed; not complete coverage |
| 1: persistent sessions | Continue the same project, recover and switch projects | Same PID, deduplication, revision conflicts, error after Save, cancellation/idle recovery, cross-MCP access | 45 tests and 24 native jobs met expectations |
| 2A: basic GUI | Managed-window observation, Win32/UIA menus/buttons/text, screenshots and dismissal | Stale-target refusal, modal COM isolation, commit/rollback read-back | 62 tests and 23 native jobs met expectations |
| 2B: complex input channel | UIA select/toggle/expand/collapse, screenshot mouse input, shortcuts and Chinese text | Control states, screenshots, commit/rollback project read-back | Source and frozen builds each completed 43 expected jobs; not every custom editor |
| 3: sharing and host installation | Bundled runtime, host selection, self-test and configuration rollback | System-only PATH, spaces/Chinese paths, actual host startup commands | Installation mechanisms, alternate paths and rollback passed; physical devices and real host models recorded separately |
| 4: coverage and delivery | Query tested capabilities/gaps; ZIP/MCPB, hashes and recovery | Frozen workflows, programs, sessions, GUI and official package validation | Matrix and release acceptance exist; complete function certification remains open |
| 5: model profiles, from 0.2.1 | Five-tool economy interface, recipes, short errors, pagination and on-demand skills | Protocol/configuration tests, then real model quality and usage | Interface checks passed; a full cross-provider cost/success benchmark remains open |

The selected identity is **Origin Companion with a blue open-circle icon**, retaining internal connection ID `origin-agent`. SVG/PNG branding and a bundled runtime are included; actual installed versions are recorded in [VALIDATION.md](VALIDATION.md).

Coverage categories are imports, sheets/matrices, 2D/3D/statistical plots, axes/legends/layout, linear/nonlinear fitting, statistical tests, signals/peaks, templates, Apps, project management and export. Discovery, execution and result acceptance are separate states; tool count is not coverage.

## Next delivery gates: real agent environments

Codex is the development tool. Release acceptance uses the work entrypoints students and staff actually use.

| Priority | User experience to verify | Current evidence or gap |
| --- | --- | --- |
| Independent installation/startup | Start in the user's own agent on a new device/account without developer paths, repository, terminal or account | Packaged/local and second-device normal-user runtime evidence exist; original second-device tool-host startup and different-user coverage remain open |
| Cloud Work | Supply data, generate figures, continue editing and receive OPJU after the development terminal exits | Real 0.2.5–0.2.8 cases; SR2 file receipt; SR1 Terra max native execution; first-connection guidance, full SR1 receipt details, reboot and long-term operation need more work |
| Local Work | Complete the same task through local Work, using a research folder if needed | Independent acceptance pending; Codex CLI/MCP clients are not substitutes |
| Other agents | Actual Claude Desktop, WorkBuddy and other host models complete the workflow | Configuration/protocol checks exist; real host/model workflows require acceptance |
| Economical models and usability | Terra max first, then available alternatives; record first-attempt success, corrections, total time and available usage | Sol/light and Terra/max Work cases exist; comprehensive model comparison remains open |

Prefer recipes/batches → general native programs → necessary GUI interaction. The agent/plugin handles API selection, execution and recovery. Ask users for information affecting the science. Requiring users to debug generated code or maintain development processes remains a usability defect.

## GUI boundaries

A GUI transaction spans calls: save a checkpoint, observe, perform one action, observe again, then commit after modal windows close. Do not call potentially blocking Origin COM save/read operations while a modal window is open. Native programs, project switching and batches cannot interleave with an unfinished transaction.

Use IDs from the latest observation and recheck process/window identity and state. Visual input is bound to the latest screenshot, client coordinates, DPI and foreground window. Project rollback cannot undo external files, network effects or global settings. General input supports custom controls, but individual tasks still need verification.

## Distribution, quality and efficiency

Use [GitHub distribution](../../PUBLIC_DISTRIBUTION.md) with English public documentation and one Windows x64 package for both builds. Make host selection and self-test clear; reuse personal configuration/keys on upgrade. Identify first-time account steps accurately. Repeat installation, reconnect and rollback are user acceptance cases, not just packaging features.

Reuse MCP, SQLite, device locks, artifact checks and existing Windows facilities. Add dependencies only for a demonstrated need. Prefer native batches, text summaries and on-demand screenshots. Measure calls, startup, execution and response size; verify quota savings from actual host usage. Keep core/protocol, native and host/model evidence separate.

See [implementation design](IMPLEMENTATION_PLAN.md), [GUI architecture](GUI.md), [model profiles](MODELS.md), [ELM](ELM.md) and [validation history](VALIDATION.md).
