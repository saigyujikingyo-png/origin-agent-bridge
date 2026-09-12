# Origin Companion 0.2.9: one OpenAI connection

Date: 2026-09-12. Scope: English public presentation, one registered OpenAI entry, reversible local-entry consolidation and packaging/connection regression. This is a preview and does not certify every Origin feature.

## Pre-upgrade host evidence

The existing registered app was installed and reconnected through ChatGPT's official UI. Its description was updated in English. The same connection was tested without creating another app or credential:

| Surface | Actual selection | Result |
| --- | --- | --- |
| Cloud Work | GPT-5.6 Terra, max reasoning | Status and import-table help passed; UI reported 25 seconds; server 0.2.8, Origin 2026b SR2 10.350243 |
| Chat | UI label Instant; provider model identifier unavailable | Both requested calls passed; actual help response inspected in the tool-call panel; server 0.2.8, latest verified Origin build 10.350243 |
| Fresh Codex CLI session | GPT-5.6 Terra, max reasoning; local Origin plugin explicitly disabled for this test only | Exactly two real `codex_apps` tool calls passed: `origin_companion.origin_status` and `origin_companion.origin_help`; server 0.2.8, build 10.350243 |
| Local Work desktop UI | Two user attempts | Blocked before Origin invocation by host project synchronisation; not inferred from Codex or browser Work |

The fresh Codex event stream contains successful tool results and reports 179,264 input tokens, 141,056 cached input tokens, 1,708 output tokens and 1,301 reasoning output tokens. Charges are unavailable. This reflects the complete configured host context, including unrelated installed plugins, not an isolated Origin tool-schema benchmark. It must not be presented as a measured quota reduction.

The calling older task still returned `Unknown tool` for its stale cloud alias. That failure and the fresh-session passes are separate evidence. Old conversations are not automatically rewritten by a plugin refresh.

## Consolidation on this computer

The registered app was checked using the installed Codex `app/read` protocol. All five expected tools were enabled. No model call is made by this setup check.

The first official local-plugin uninstall failed while older plugin processes held its cache. Configuration was restored. After identifying and closing only the old local Origin MCP servers and their PowerShell wrappers, the consolidation retry succeeded. The running cloud tunnel, Codex application and Origin application were preserved. The personal catalog retained its unrelated entry; the retired Origin source folder remains available for rollback. After the user reported a local Work failure, that receipt was rolled back and the official local plugin was reinstalled as a temporary fallback. The initial error was subsequently traced to host project synchronisation, not an Origin tool call. Final consolidation used the installed 0.2.9 executable. An initial attempt again encountered a Windows cache sharing violation and restored its configuration. After closing only identified old local Origin servers with no child jobs, official removal and the targeted catalog migration succeeded. The final personal catalog has no local Origin entry; the same registered OpenAI app remains enabled with five tools. The existing scheduled private tunnel was restarted and verified running the 0.2.9 executable, with its account profile and encrypted key reused.

Private app IDs, account URLs, credentials, machine identifiers and detailed local logs are excluded from this public report. They are stored only in the local installation receipt.

## Local Work project synchronisation incident

The user reported **"Could not use this project for a local chat"**. The desktop log recorded `ChatGPT project context sync failed` at `stage=filesystem`, with zero source files and no Origin call. A read-only directory-access check returned Windows sharing violation 32 for the project root, while its instruction file and sources directory allowed access. Four existing desktop tool processes had that project directory as their current working directory; related tasks were active. Those tasks and files were preserved.

This establishes a host project-cache replacement conflict, rather than a missing Origin operation. The user then retried a projectless local Work task and reported the same message; new filesystem-stage log failures were present. The first workaround therefore failed. After confirming the related task had completed, four idle helper processes were reset once; the host immediately recreated them with the same project working directory, and the sharing violation remained. No repeated process killing, proprietary application patch, cache deletion or Origin credential replacement was performed. The user subsequently fully restarted the desktop client, which updated to 26.908.4834.0. Fresh logs still recorded the same filesystem-stage failure and a read-only root check still returned sharing violation 32. Restart is a failed recovery attempt for this session. Local Work UI acceptance on this machine remains blocked by the host project-sync behavior; it has not been repaired by replacing the plugin registration.

## 0.2.9 validation

- Local suite: 174 passed, one skipped because Windows symlink permission was unavailable.
- Ruff lint and formatting passed; graphical setup PowerShell syntax parsed successfully.
- New checks cover invalid links/keys, incorrect or unavailable app identities, unrelated-plugin preservation, failed CLI rollback, repeat consolidation, unfamiliar direct MCP entries, legacy installer routing, and real MCP initialization with the same title/icon in economy/full modes.
- GitHub Windows and Ubuntu checks passed for runtime commit `da4f14f167e663fdbd92bfed6d46db7d3d3f0655`: [CI run](https://github.com/saigyujikingyo-png/origin-agent-bridge/actions/runs/34699408989).
- Official MCPB manifest validation and Codex plugin validation passed on the built bundle. The MCPB validator recommends a 512 px icon; the current icon is valid.
- ZIP and MCPB are byte-identical: 33,089,607 bytes each (31.56 MiB), SHA-256 `1f2006e641064f21beef69b01ff9d918bcf7ffde9b5af4503532286ac1ff3b23`. All 310 archive entries and individual file hashes were verified.
- Isolated installation into a user path containing spaces, repeat installation and current-user upgrade from 0.2.8 passed, including native self-checks. Installation receipts and the previous version were retained.
- The frozen executable ran with development runtimes removed from PATH. A synthetic six-row Beer-Lambert workflow passed independent slope/intercept/unknown-concentration checks, native project/report/text reopening, and PNG/PDF/SVG/OPJU byte-count and SHA-256 verification. Workflow elapsed 26.578 seconds; the complete regression including intentional-failure recovery took 42.219 seconds. No model was called in this regression.
- The native PNG was visually inspected: six standards, fit line, legend and axis labels were readable. This is a synthetic packaging regression, not a claim of compliance with every course's figure requirements.
- A deliberately missing Python dependency returned a terminal failure and actionable recovery instead of continued polling.
- The installed Claude and WorkBuddy commands each returned 0.2.9 and the five-tool economy interface. These are command/protocol tests, not actual model-session acceptance for those hosts.
- The new graphical connection window has passed syntax and code checks but has not had interactive desktop acceptance.

## Post-upgrade hosted connection checks

After the existing private tunnel restarted on the installed 0.2.9 core:

- Cloud Work, GPT-5.6 Terra with max reasoning: a new status call returned **0.2.9**, Origin build **10.350243**; import-table help also succeeded. The expanded activity showed the requested actions; the UI reported 12 seconds for this two-call check.
- Chat, UI label Instant: a new status call returned **0.2.9**. Its actual request and response were inspected in the tool-call panel.
- A fresh Codex Terra max attempt mistakenly called the browser state tool and stopped without calling Origin. This is a model tool-selection failure, not an Origin execution failure. It used 42,436 input tokens (29,184 cached), 1,030 output tokens and 918 reasoning output tokens; charges were unavailable. A corrected prompt explicitly selecting the connected app was then tested separately: exactly one real `codex_apps` call to `origin_companion.origin_status` succeeded with **0.2.9**. The returned server metadata included the English title/description and blue icon URL. The retry used 62,090 input tokens (38,400 cached), 331 output tokens and 208 reasoning output tokens. Count the earlier failure and correction when assessing first-attempt reliability; these mixed host-context runs are not an isolated quota-saving benchmark.

## Registered icon replacement follow-up

The user approved replacing the iconless account registration and deleting the old registration after acceptance. ChatGPT's creation form required a PNG no larger than 10 KB and recommended at least 256 x 256 pixels; the existing 512 px PNG exceeded that limit. The existing vector artwork was exported as `origin-agent/assets/icon-chatgpt.png` (256 x 256, 7,666 bytes). PNG structure, chunk checksums and the saved listing image were checked. No runtime dependency was added.

The replacement reused the existing private tunnel and encrypted credentials. It was connected and tested under a temporary verification name, then the old registration was deleted through the official UI and the replacement renamed **Origin Companion**. The account-local link was updated with a reversible receipt. A fresh personal-catalog search showed exactly one Origin Companion; its blue icon remained visible after reopening the page. The runtime stayed at **0.2.9**. The listing's generic 1.0.0 metadata is not the execution-core version.

| Post-retirement surface | Actual check | Evidence and result |
| --- | --- | --- |
| Chat, UI label Instant | One `origin_status` | Passed, 0.2.9; actual request and response inspected and mapped to the retained registration |
| Cloud Work, GPT-5.6 Terra max | `origin_status`, then `origin_help` for `origin_import_table` | Passed, 0.2.9; response and activity observed, UI 24 seconds; raw Work tool-response payload not exposed in the inspected UI |
| Fresh Codex CLI, GPT-5.6 Terra max, first attempt | One `origin_status` | Failed with `Unknown tool` while generated tool metadata still contained the retired registration and the temporary replacement name |
| Fresh Codex CLI, GPT-5.6 Terra max, after refresh | One `origin_status` | Passed, `isError: false`, 0.2.9; actual event stream inspected; complete process 20.39 seconds |
| Local Work desktop 26.908.4834.0 | User retry after full restart | Still blocked before any Origin call by the project-sync error described above |

After the final registered metadata refresh, the official app-server MCP reload/list check advertised exactly five Origin tools under the final name, all pointing to the retained registration. The old identity was absent. No tool-cache JSON or application binary was manually rewritten. The successful Codex retry followed this check; existing conversation aliases are not certified to migrate automatically.

The failed Codex attempt used 63,140 input tokens (39,424 cached), 869 output tokens and 713 reasoning output tokens. The successful retry used 41,172 input tokens (18,176 cached), 715 output tokens and 533 reasoning output tokens. Charges and Chat/Work usage were unavailable. These include the configured host context and are not an isolated efficiency comparison. The pre-retirement Work status pass (15 seconds) was a separate check and was not substituted for post-retirement acceptance.

No scientific jobs or user datasets were processed for the icon repair. Earlier native workflow checks remain the scientific evidence for the unchanged executable; these new checks validate the replacement connection only.

## Publication verification

The public v0.2.9 preview contains both archives and the checksum file. GitHub's asset digests match the recorded SHA-256. The ZIP was downloaded back from the public release and independently verified at 33,089,607 bytes with the same digest. All 309 files covered by the installed bundle's checksum manifest also match.

Documentation erratum: the bundled advanced generic-MCP example retains the older `host-configs/0.2.8` path. For 0.2.9 use `host-configs/0.2.9/generic-mcp.json`; the online installation guide and release note are corrected. Runtime-generated configurations already use the correct version. Published archive bytes were preserved.

The separate `icon-chatgpt.png` and `icon-chatgpt.sha256` release assets were subsequently uploaded and downloaded back for verification. The PNG is 7,666 bytes, SHA-256 `d0f86b5a84a96ff2a4aff67680f7aea860071d639d9f7a2335174a4ff84c7ae7`. Both original archive digests and the original `SHA256SUMS.json` digest were checked unchanged. The image is a separate listing asset, not a replacement runtime bundle.

## Remaining limits

The runtime is still an independent personal-sharing preview for the two stated Origin builds. Previous native/NIST and cloud artifact results remain in [0.2.8 acceptance](WORK_ACCEPTANCE_0.2.8.md). These connection checks do not replace complete workflow and artifact acceptance in each host. Local Work, broader models/agents, complete SR1 artifact receipt and complete Origin coverage remain separately tracked.
