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

The first official local-plugin uninstall failed while older plugin processes held its cache. Configuration was restored. After identifying and closing only the old local Origin MCP servers and their PowerShell wrappers, the consolidation retry succeeded. The running cloud tunnel, Codex application and Origin application were preserved. The personal catalog retained its unrelated entry; the retired Origin source folder remains available for rollback. After the user reported a local Work failure, that receipt was rolled back and the official local plugin was reinstalled as a temporary fallback. The initial error was subsequently traced to host project synchronisation, not an Origin tool call. Final consolidation status is recorded below after retesting.

Private app IDs, account URLs, credentials, machine identifiers and detailed local logs are excluded from this public report. They are stored only in the local installation receipt.

## Local Work project synchronisation incident

The user reported **"Could not use this project for a local chat"**. The desktop log recorded `ChatGPT project context sync failed` at `stage=filesystem`, with zero source files and no Origin call. A read-only directory-access check returned Windows sharing violation 32 for the project root, while its instruction file and sources directory allowed access. Four existing desktop tool processes had that project directory as their current working directory; related tasks were active. Those tasks and files were preserved.

This establishes a host project-cache replacement conflict, rather than a missing Origin operation. The user then retried a projectless local Work task and reported the same message; new filesystem-stage log failures were present. The first workaround therefore failed. After confirming the related task had completed, four idle helper processes were reset once; the host immediately recreated them with the same project working directory, and the sharing violation remained. No repeated process killing, proprietary application patch, cache deletion or Origin credential replacement was performed. Local Work UI acceptance on this machine remains blocked by the host project-sync behavior; a new application session or host fix must be verified separately.

## 0.2.9 validation

- Local suite: 174 passed, one skipped because Windows symlink permission was unavailable.
- Ruff lint and formatting passed; graphical setup PowerShell syntax parsed successfully.
- New checks cover invalid links/keys, incorrect or unavailable app identities, unrelated-plugin preservation, failed CLI rollback, repeat consolidation, unfamiliar direct MCP entries, legacy installer routing, and real MCP initialization with the same title/icon in economy/full modes.
- Frozen-package, installed-native, final hosted-version and CI results are added below after they run. The new graphical window has not yet had interactive desktop acceptance.

## Remaining limits

The runtime is still an independent personal-sharing preview for the two stated Origin builds. Previous native/NIST and cloud artifact results remain in [0.2.8 acceptance](WORK_ACCEPTANCE_0.2.8.md). These connection checks do not replace complete workflow and artifact acceptance in each host. Local Work, broader models/agents, complete SR1 artifact receipt and complete Origin coverage remain separately tracked.
