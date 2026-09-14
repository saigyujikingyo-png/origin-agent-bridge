# Origin Companion

<img src="assets/icon.svg" alt="Origin Companion" width="80" height="80">

Your agent, your Origin. Independent personal project; not an official OriginLab or university product.

**Open-source and unified across agent hosts.** The target is the same Origin Companion for ChatGPT Chat, local Work, cloud Work, Codex, Claude Desktop, WorkBuddy and other suitable agents, with a shared execution core. Codex is also used to develop and maintain the plugin. End users install the packaged plugin, connect their own host, and request scientific work in natural language. A source checkout, Git repository, development terminal and separately installed Python are not runtime prerequisites.

Cloud Work has recorded real-model acceptance. Local Work and other hosts need their own end-to-end acceptance; a successful Codex CLI or standalone MCP client test does not certify those user flows. See the [current Work acceptance report](https://github.com/saigyujikingyo-png/origin-agent-bridge/blob/codex/origin-companion-release/WORK_ACCEPTANCE_0.2.8.md).

The target is a smooth Origin plugin for licensed University of Edinburgh staff and students. See the [Edinburgh product definition and reuse assessment](docs/EDINBURGH_PRODUCT.md). Version 0.2 includes native programming, live projects, GUI input and a self-contained Windows installer. Coverage is recorded by verified example, not by assuming that every function works.

Agent-neutral, local Origin workflows over MCP. The personal sharing build accepts **Origin 2026 SR1 (10.300197) and 2026b SR2 (10.350243), Windows x64, Origin edition**. Native workers check the exact build, bitness, edition and non-Demo activation. SR2 has documented native acceptance cases; SR1 has passed four native NIST cases and a Terra max cloud Norris workflow on a second device; complete cloud receipt details and the original tool-host launch context remain open. Matching the version does not certify all workflows. This project does not distribute Origin or a licence.

Version 0.2 adds general Python/originpro/COM, LabTalk/X-Function and Origin C execution, installed capability discovery, persistent managed sessions and a native GUI transaction channel. Fourteen full-mode MCP tools cover workflows, capabilities, session/GUI control and artifacts without registering one tool per Origin function. Programs run as trusted code with the Windows user's permissions.

The fixed workflow route remains available for CSV/TSV/XLSX import, multi-Y plotting, error bars, linear regression and Beer–Lambert calibration with independent numerical checks. Independent programs reopen their saved OPJU for structural verification; session programs preserve the live project and report that no reopen check occurred. Session revisions reject stale edits and failed operations restore project checkpoints. Execution checks do not establish scientific correctness.

The product target is access to the complete functionality of the user's licensed Origin edition. **Full GUI coverage and universal function validation are not complete.** See [FULL_ORIGIN.md](docs/FULL_ORIGIN.md) for the implementation contract and remaining work.

Use the installation packages described in [INSTALL.md](docs/INSTALL.md). The Windows package includes its execution runtime. Cloud access uses the user's supported authenticated connection to that Windows installation; the model remains in the selected agent host. First-time cloud connection setup still requires account-specific steps and is a remaining usability improvement.

[Historical initial design](../INITIAL_DESIGN.md) records the original proposal. Source layout and performance decisions: [ARCHITECTURE.md](docs/ARCHITECTURE.md). Current measured evidence and limitations: [VALIDATION.md](docs/VALIDATION.md).

<details>
<summary>Developer setup — for modifying this project</summary>

Use Codex or another development environment with a source checkout. Run `uv sync --locked`, then `uv run origin-agent serve` from the `origin-agent` package directory. This source workflow is separate from the packaged end-user installation. For ordinary agent work, including Codex, use the packaged plugin connection; these source commands are for modifying the project.

</details>

The phases and acceptance gates are in [ROADMAP.md](docs/ROADMAP.md), with module design in [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md). Persistent sessions and [GUI transactions](docs/GUI.md), including UIA, mouse, keyboard and Unicode input, have passed recorded native cases. Query `origin_capabilities("coverage")` for the [coverage matrix](docs/COVERAGE.md). The stable internal ID `origin-agent` preserves existing MCP connections; the display name and blue open-circle icon are Origin Companion.

Try a complete natural-language workflow using the [synthetic example](examples/README.md).

## Models and economy mode

[Model profiles](docs/MODELS.md) cover DeepSeek, GPT Terra, Gemini, GLM, Kimi and ELM-capable hosts. The five-tool economy interface loads operation arguments on demand, offers simple recipes and paginates text; the full 14-tool interface remains available. See [ELM models and quota boundaries](docs/ELM.md). Presets are not model-success certifications, and the plugin does not make extra model API calls.

## Recent changes

- **0.2.11:** Strict output schemas, validated structured results, safe malformed-output recovery, and compatible media metadata. [Output contracts](docs/OUTPUT_CONTRACTS.md).
- **0.2.10:** WorkBuddy feedback fixes: recover wrapped help requests, separate optional model recommendations, report unsupported inverse-calibration uncertainty in structured form, and save/recheck per-axis scientific notation. [Acceptance and limitations](https://github.com/saigyujikingyo-png/origin-agent-bridge/blob/codex/origin-companion-release/WORK_ACCEPTANCE_0.2.10.md).
- **0.2.9:** one registered OpenAI connection for Chat, Work and Codex, a graphical account-link setup, guarded consolidation of old local entries, and consistent English name/icon metadata. See [unified setup](docs/UNIFIED_PLUGIN.md). Local Work desktop acceptance remains separate.

- **0.2.8:** accepts the two explicit Origin builds, reports the execution computer for routing, and returns bounded structured errors for correctable input, plan and syntax problems. Native and actual Work evidence is recorded by device; complete coverage remains unverified.
- **0.2.7:** adds verified binary downloads over the existing private MCP connection. Hosts that do not create files from embedded resources can request the built-in receiver on demand; it saves and verifies bytes without browser globals or a persistent terminal. Numeric Unicode superscripts/subscripts use Origin rich text to avoid missing-glyph boxes. No added runtime dependency or model API. See [file delivery](skills/origin-workflow/references/FILE_DELIVERY.md).
- **0.2.6:** adds direct CSV/TSV text import and a simpler Beer–Lambert recipe. Failed jobs explicitly stop polling and provide recovery guidance. Standard fits reuse the verified native workflow without temporary Python or NumPy. Economy mode retains five tools; full mode has 14.
- **0.2.5:** adds a private-tunnel login task independent of Codex; fixes figure titles/wrapping, matrix project snapshots, worksheet errors and fit notes. It uses the current Windows user and existing tunnel. The resident supervisor retries unexpected process exits after 5/15/30 seconds and resets after five stable minutes. See [Work troubleshooting](docs/WORK_TROUBLESHOOTING.md).
- **0.2.2:** accepts cached full-mode tool names after switching to economy mode, preserving argument, vision and session checks while advertising only five tools. Old host conversations may still need a refresh or a new conversation.
