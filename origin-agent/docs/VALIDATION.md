# Validation history

These are dated acceptance records, primarily from **2026-09-11**. Each section describes the code and installation at that stage; later passes do not erase earlier failures or certify earlier untested combinations. Inputs were synthetic unless stated otherwise. For the current public preview and second-device evidence, read [0.2.8 acceptance](../../WORK_ACCEPTANCE_0.2.8.md).

## 0.1.0: installed native workflow

Verified standard Origin 2026b SR2 (10.350243), Windows x64, non-Demo. Official originpro 1.1.15 / OriginExt 1.2.5 created a separate instance. `scripts/verify_native.py` used real stdio MCP for inspection, batch planning, queueing, fitting/export, project inspection and preview, then repeated submission to verify deduplication and saved `acceptance.json`.

| Check | Result |
| --- | --- |
| Automated tests | Windows Python 3.12: 19 passed in 14.54 seconds; Ruff passed |
| Clean CI | Locked install, Ruff and 19 tests passed on Ubuntu/Windows; [run](https://github.com/saigyujikingyo-png/origin-agent-bridge/actions/runs/34565734250) |
| Runtime independence | Installed frozen EXE succeeded with PATH limited to System32 and no PYTHONPATH/PYTHONHOME |
| Paths | Complete workflow under paths containing Chinese characters and spaces |
| Native execution | Three figures, two linear fits: free/zero intercept, errors, multi-Y and Beer–Lambert unknown |
| Reopen/read-back | All data-column hashes matched; three graphs and two native reports existed |
| Numerical checks | Coefficients, RSS and sample size matched independent least squares; errors were not silently weights |
| Outputs | OPJU, three PNG/PDF/SVG sets, two fit JSON/residual CSV sets and provenance/verification manifest |
| Images | PNG decoded; figures 1 and 3 visually checked for readable axes, errors, legends and curves without legend obstruction |
| Deduplication | Same plan returned the original job ID |
| MCP/HTTP | Eight tools; in-process SDK, real stdio auto/legacy and loopback Streamable HTTP passed; foreign Host rejected |
| Artifact access | Hash tampering and path traversal rejected |

Installed-run cold MCP connection: 2.235 seconds. Native connection/calculation/export/reopen: 46.578 seconds. Full inspection/planning/wait/preview: 52.344 seconds. A preceding similar packaged test took about 27 seconds; load and Origin cold start affect timing. Neither is a throughput/latency guarantee.

Tool descriptions serialised to 7,969 characters, not actual model tokens or account savings. ZIP/MCPB were about 31.22 MiB, with no additional model API dependency. Unit/protocol cases covered missing science, invalid values, scope, snapshot/plan tampering, Excel formulas, known answers, concurrent deduplication, cancellation, locks, Windows sharing retries and official SDK connections.

### Hosts and accounts at 0.1.0

Actual installed Claude Desktop, WorkBuddy and Codex-cache launch configurations each connected through an official MCP client, discovered eight tools and called status, sharing `.origin-agent/inbox`. These were configuration/protocol checks, not all host-model workflows.

- Codex personal plugin 0.1.0 installed; a new conversation was required to load it.
- Claude Desktop configuration backed up/merged; restart and actual model acceptance remained open.
- WorkBuddy 5.3.5 configuration backed up/merged and skill installed, preserving other services; logs confirmed connector refresh read that configuration. Model acceptance remained open.
- ChatGPT private tunnel/account association and developer plugin were installed with eight tools. Official Windows tunnel-client 0.0.14 was hash-verified; process_running/healthy/ready were true. The user created a Tunnels Read/Use-only key with model API permissions disabled and stored it encrypted locally.
- Actual ChatGPT natural-language workflow imported synthetic data, planned, fitted OLS in Origin, exported/reopened, inspected the project, displayed PNG and reported results. Job `22dffe6f92f04e22b4daf7036ee32971`: native 20.469 seconds, slope 0.2004, intercept 0.0992, RSS 0.0002304, OPJU 130,284 bytes.
- The model initially supplied a wrong field; validation rejected it and the model corrected it before native execution. PNG materialisation needed one host permission. Cloud OPJU download was not directly tested; the Windows file opened locally.
- Portable packaging generated local paths, but a second physical computer had not been tested at that stage.

Installed native job: `ac399f49e7d44c95908dbf313a510e8c`. Full JSON/OPJU evidence stayed on the test computer. Other builds/devices and remaining host models required separate acceptance.

## 0.2 source prototype: general native programs

On 2026-09-11, source passed 29 unit/protocol tests, Ruff and plugin/skill validation. Real MCP called a separate worker on the same standard SR2 build.

| Case | Result | Native time |
| --- | --- | ---: |
| Python ExpDec1 | Noise-free data recovered A1=2, t1=1.4, y0=0.3; report/curve/OPJU/images and numerical expectations passed | 23.641 s |
| Edit an OPJU copy | Axis title changed, saved and reopened with matching structure | 14.250 s |
| LabTalk/X-Functions | newbook, column operations, total=55, type log and postconditions | 13.094 s |
| Origin C | Local compilation, square(7)=49 and postconditions | 12.578 s |

Two real API differences were corrected: LabTalk `sum` returns cumulative data, so use `total` or `sum.total` for a total; `run.LoadOC` required Windows backslashes on this build, with forward slashes returning code 3. Failed expectations stayed failed. `type` did not capture every X-Function `-h` output.

Initial discovery found 799 X-Function files, 305 fitting-function files and 305 Python API index entries. Counts are not licence/acceptance/coverage totals. Native figures were viewed; general-program reopen established structure, not complete numerical or independent scientific verification. Evidence: `.origin-agent/verification/general-source-020/acceptance-programs.json`. This stage had not yet packaged/replaced installed 0.1.0 or tested the new tools in actual host models/full GUI/other devices.

### Exact build and candidate evaluation

The personal-sharing requirement added exact build, bitness, edition and non-Demo checks. Tests increased to 37 passes; unprobed installations and native-verified targets were distinguished, retaining the false complete-function flag. The four native cases passed again: nonlinear 21.51 s, OPJU edit 14.23 s, LabTalk 11.75 s, Origin C 11.66 s. Evidence: `.local/target-020-native/acceptance-programs.json`.

[Ge-Shun v0.1.4 evaluation](CANDIDATE_EVALUATION.md) made 17 MCP calls, eight passing checks and one failed structured nonlinear fit that reported outer success without executing. Evidence: `.local/candidate-validation/run-02/candidate-report.json`; it is not a passed Origin Companion release.

## 0.2 source: persistent sessions

Sessions, revision conflicts, checkpoints/recovery and the shared queue passed **45 tests in 15.21 seconds**, Ruff and skill validation. Source exposed 11 tools with a 28,000-character schema regression limit, not a token/cost measurement. No runtime dependency, listener or model API was added.

Two real stdio suites used synthetic data and separate state directories; **24 native jobs**, including expected failure/cancellation, all met their criteria:

| Suite | Cases | Local evidence |
| --- | --- | --- |
| `verify_sessions.py`, 12 jobs | Same PID edits, stale refusal, error read-back, checkpoint restore, cancellation recovery, hidden idle exit/wake, close | `.local/session-native-02/acceptance-sessions.json` |
| `verify_session_switching.py`, 12 jobs | Error after ordinary Save, visible idle retention, foreign-checkpoint refusal, two-project/batch switching and close | `.local/session-switch-01/acceptance-switching.json` |

Repeated requests reused a job; a second MCP process read the same revision/PID. The Save test established the need to switch back to `working.opju` after creating an immutable recovery snapshot so ordinary Save cannot overwrite it. No test Origin instances remained.

| Operation | End-to-end | Native |
| --- | ---: | ---: |
| Initial session open | 14.516 s | 11.234 s |
| Create sheet in session | 1.594 s | 0.875 s |
| Edit existing sheet | 1.062 s | 0.594 s |

These small local observations do not predict large-project, GUI or other-device performance. Live sessions do not reopen after every change, so `project_reopened` and `structure_roundtrip` were false; explicit native read-back checked these cases. Recovery covers the project, not external effects. This was still unpublished source, with installed 0.1.0 retained and new GUI/package/host/device acceptance open.

## 0.2 source: basic GUI and branding

`origin_gui` brought the source to 12 tools and a 32,000-character schema limit. **62 tests passed in 16.72 seconds**, plus Ruff/manifest/skill checks. Added dependency: Windows comtypes 1.4.16; no new service/model API.

Real `verify_gui.py` evidence at `.local/gui-acceptance-06/acceptance-gui.json`: **23 expected outcomes, 19 successes and four refusals**, 91.609 seconds, ten valid screenshots and no capture error in the final run.

| Check | Result |
| --- | --- |
| Menus/Properties | UIA Window → Properties, native Edit/OK and residual MFC-menu dismissal |
| Commit/read-back | Long name `Origin Companion GUI verified`, data `[1,2,3]`, saved OPJU |
| Modal rollback | Uncommitted edit discarded by restarting only owned Origin and restoring begin checkpoint; name/data matched |
| Stale observation | Old observation_id rejected without input |
| Isolation | Programs, independent batches and modal commit rejected during the transaction |
| Close | Synthetic project saved and closed |

MCP edit 1.609 s, commit 4.203 s, modal rollback requiring restart 18.141 s. Dialog screenshots and native name/data assertions were checked. One Properties case does not certify all dialogs/custom editors or science.

Exploration found and fixed empty/duplicate MFC IDs, leftover menus, disappearing-dialog reads, stale OriginExt reconnect objects, transient Windows sharing and capture-failure handling after a successful save. Failed explorations remain separate from final passes.

The user selected **Origin Companion and a blue open-circle icon**. Source/host metadata and local Codex cache were refreshed; display name and SVG hash matched while preserving `origin-agent`. The installed engine was still 0.1.0 at this stage; new GUI host-model/second-device acceptance had not happened.

## 0.2 frozen package: extended GUI and installation

UIA selection/toggle/expand/collapse/value and observation-bound clicks, drag selection, scroll, shortcuts and Unicode were implemented, alongside native installation self-test, configuration merging/backups, failure recovery and conflict-aware rollback. Twelve tools and one runtime stack were retained; **80 local tests** and Ruff passed on standard SR2.

| Frozen suite | Result | Local evidence |
| --- | --- | --- |
| Extended GUI | 43 expected jobs: 39 success/four refusals, 107.687 s; Chinese, selection, scroll, toggle, commit/modal rollback read-back | `.local/gui-frozen-020-01/acceptance-gui.json` |
| General programs | ExpDec1 parameters, copied OPJU edit, LabTalk total 55, Origin C square(7)=49 | `.local/frozen-020-r2-programs/acceptance-programs.json` |
| Sessions | 12 expected jobs: failure/cancellation recovery, stale revision and idle wake | `.local/frozen-020-r2-sessions/acceptance-sessions.json` |
| Project switching | 12 expected jobs: Save/error recovery, visible retention, foreign checkpoint and batch coexistence | `.local/frozen-020-r2-session_switching/acceptance-switching.json` |
| Fixed workflow | Three graphs, two reports, data read-back, OPJU reopen, PNG/PDF/SVG; figures viewed; native 22.109 s | `.local/frozen-020-r2-native/acceptance.json` |
| Portable install | Chinese/spaces path, System32-only PATH, no external Python/Node, actual self-test, simulated Claude/WorkBuddy config and seven-file rollback | `.local/portable 中文验收/State/installations/87ca351acbd949539876a656ae7f7929/receipt.json` |

Frozen total: **72 expected jobs: 63 success, eight expected refusals/failures, one expected cancellation**. Separate source extended GUI: 43 jobs in 111.718 seconds, not counted twice.

An initial copied-OPJU edit timed out while Windows entered modern standby after lid closure. Kernel-Power 506/507 recorded wake about ten minutes later by the power button. The same synthetic file reopened and all four program regressions passed afterwards; the earlier failure remains excluded from passes. Execution during sleep/lid closure is not promised.

Official `@anthropic-ai/mcpb` validation required a PNG icon; the selected SVG was exported unchanged at 512×512 and validation passed. ZIP/MCPB were about 31.7 MiB, with no Node runtime dependency. SVG remains for other hosts; package hashes are integrity checks, not publisher code signatures.

Complete-function status remained false. Matrix/3D/statistics/signals/peaks/custom editors/Apps and actual other-device/host models needed separate checks at that time. See [COVERAGE.md](COVERAGE.md); earlier "not yet installed" statements describe their original stages.

## 0.2.1: model interfaces and local upgrade

Added full/economy modes and generic, DeepSeek, GPT Terra, Gemini, GLM, Kimi and ELM profiles. The user's Terra preference retains **max**; the plugin does not change the host model. **104 tests passed in 30.04 seconds**, plus Ruff, including both stdio negotiations/HTTP, validation/deduplication, syntax locations, non-echoing errors, text-only restrictions and precedence.

Tool JSON measured full 19,514 bytes versus economy 4,372, 77.60% smaller, from `benchmark_profiles.py`, not billing. All 13 operation schemas remained available through economy; recipes reused validation/deduplication and skills loaded references on demand.

0.2.0's actual installation receipt was `4b0d06eb4307490a9c8f882c0e0029a6`. Claude/WorkBuddy/Codex startup commands exposed 12 tools before upgrading; configuration is not model execution.

Frozen economy completed two native jobs in 37.734 seconds: synthetic slope 2/intercept 1 with report/reopen; general read-back [7,14,21] and explicit cell total 42. Identical recipes reused the job; paginated manifest reconstruction matched the local file, and the figure was viewed. Evidence: `.local/frozen-021-economy-r2/acceptance-economy.json`.

The initial fixture used `sum(col(A))`, which evaluated to 7 instead of 42 and correctly failed. Replacing it with `col(A)[1]+col(A)[2]+col(A)[3]` fixed the fixture, not the runtime. The first failure remains at `.local/frozen-021-economy`. Installed version/receipts/host commands/tunnel state were recorded separately; cross-provider and second-device acceptance were still open.

Frozen 0.2.1 GUI regression: 43 expected jobs, 39 successes/four refusals or failures, 104.563 seconds; Chinese, drag, scroll, UIA/value/toggle, commit and modal rollback. Evidence: `.local/frozen-021-gui/acceptance-gui.json`.

## 0.2.2: cached Work tool compatibility

Installed 0.2.1 with synthetic CSV reproduced `Unknown tool` for direct economy `origin_inspect_dataset`, while `origin_call` worked. 0.2.2 accepts cached full-mode names without expanding the advertised economy list, retaining unknown-name, argument, vision and session checks.

- 105 tests passed, including real stdio auto/legacy and full/economy; Ruff lint/format passed.
- Frozen economy used old names for inspect → plan → run → get_job → inspect_project. Three synthetic figures, two native reports and OPJU reopen passed; PNG/PDF/SVG exported and all PNG labels/cropping checked.
- Five advertised tools, 4,743 JSON characters; cold start 0.984 s and workflow 28.219 s. These are single local measurements, not model/billing metrics.
- A separate Windows project-sync lock was released; that was not an engine change. See [troubleshooting](WORK_TROUBLESHOOTING.md). Actual Work UI/model flow remained a distinct check.

### Actual cloud Work follow-up

The original failing cloud task then used installed 0.2.2 over its existing private tunnel to inspect, plan, run, wait, inspect OPJU and preview four-point synthetic CSV. Slope 0.2, intercept 0.1, R²=1; one graph/native report and data reopen passed, native 11.172 seconds. Actual OPJU/PNG/PDF/SVG sizes/hashes were independently checked; PNG viewed locally and in the cloud. No Drive or real coursework was accessed.

A PDF-info read returned `UNAVAILABLE / Connection failed` and later succeeded on a read-only retry with matching path, size and hash. This establishes recovery, not uninterrupted availability. The visible model was GPT-5.6 Sol/light; the `gpt-terra` interface preset does not count as Terra, cross-model or second-device testing.

The cloud directory refreshed from eight early tools to five economy tools and the Origin Companion display name, retaining app/tunnel/permissions. The existing task still held old tools. A new authorised task successfully called status, `origin_help(query="")` and `origin_call` for capabilities, seeing five tools, 13 operations and 11 categories. It did not execute GUI/general programs. See [cloud-work-0.2.2.json](../verification/cloud-work-0.2.2.json). Discovery does not certify full functionality or rewrite original installation receipts.
