# Origin Companion

<img src="assets/icon.svg" alt="Origin Companion" width="80" height="80">

Your agent, your Origin. Independent personal project; not an official OriginLab or university product.

**Built and maintained with Codex; used in general agent work environments.** The primary product scenarios are cloud Work, local Work, Claude Desktop, WorkBuddy and other supported agent hosts. End users install the packaged plugin, connect their own host, and request scientific work in natural language. A source checkout, Git repository, development terminal and separately installed Python are not runtime prerequisites.

Cloud Work has recorded real-model acceptance. Local Work and other hosts need their own end-to-end acceptance; a successful Codex CLI or standalone MCP client test does not certify those user flows. See the [current Work acceptance report](https://github.com/saigyujikingyo-png/origin-agent-bridge/blob/codex/origin-companion-release/WORK_ACCEPTANCE_2026-09-11.md).

The target is a smooth Origin plugin for licensed University of Edinburgh staff and students. See the [Edinburgh product definition and reuse assessment](docs/EDINBURGH_PRODUCT.md). Version 0.2 includes native programming, live projects, GUI input and a self-contained Windows installer. Coverage is recorded by verified example, not by assuming that every function works.

Agent-neutral, local Origin workflows over MCP. The personal sharing build accepts **Origin 2026 SR1 (10.300197) and 2026b SR2 (10.350243), Windows x64, Origin edition**. Native workers check the exact build, bitness, edition and non-Demo activation. SR2 has documented native acceptance cases; SR1 qualification on a second device is pending. Matching the version does not certify all workflows. This project does not distribute Origin or a licence.

Version 0.2 adds general Python/originpro/COM, LabTalk/X-Function and Origin C execution, installed capability discovery, persistent managed sessions and a native GUI transaction channel. Fourteen full-mode MCP tools cover workflows, capabilities, session/GUI control and artifacts without registering one tool per Origin function. Programs run as trusted code with the Windows user's permissions.

The fixed workflow route remains available for CSV/TSV/XLSX import, multi-Y plotting, error bars, linear regression and Beer–Lambert calibration with independent numerical checks. Independent programs reopen their saved OPJU for structural verification; session programs preserve the live project and report that no reopen check occurred. Session revisions reject stale edits and failed operations restore project checkpoints. Execution checks do not establish scientific correctness.

The product target is access to the complete functionality of the user's licensed Origin edition. **Full GUI coverage and universal function validation are not complete.** See [FULL_ORIGIN.md](docs/FULL_ORIGIN.md) for the implementation contract and remaining work.

Use the installation packages described in [INSTALL.md](docs/INSTALL.md). The Windows package includes its execution runtime. Cloud access uses the user's supported authenticated connection to that Windows installation; the model remains in the selected agent host. First-time cloud connection setup still requires account-specific steps and is a remaining usability improvement.

Source layout and performance decisions: [ARCHITECTURE.md](docs/ARCHITECTURE.md). Current measured evidence and limitations: [VALIDATION.md](docs/VALIDATION.md).

<details>
<summary>Developer setup — for modifying this project</summary>

Use Codex or another development environment with a source checkout. Run `uv sync --locked`, then `uv run origin-agent serve` from the `origin-agent` package directory. This source workflow is separate from the packaged end-user installation. Codex and Claude Code integrations remain available for development and compatibility testing.

</details>

The phases and acceptance gates are in [ROADMAP.md](docs/ROADMAP.md), with module design in [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md). Persistent sessions and [GUI transactions](docs/GUI.md), including UIA, mouse, keyboard and Unicode input, have passed recorded native cases. Query `origin_capabilities("coverage")` for the [coverage matrix](docs/COVERAGE.md). The stable internal ID `origin-agent` preserves existing MCP connections; the display name and blue open-circle icon are Origin Companion.

Try a complete natural-language workflow using the [synthetic example](examples/README.md).

## 多模型与经济模式（0.2.1）

[多模型配置](docs/MODELS.md)支持 DeepSeek、GPT Terra、Gemini、GLM、Kimi 与 ELM 宿主预设。5 工具经济接口按需加载全部操作参数，常见配方使用短参数，文本输出可分页；完整 14 工具接口仍可选择。[ELM 提供的模型与额度边界](docs/ELM.md)。预设适配不是实际模型成功率认证，插件不额外调用模型 API。

0.2.5 增加独立于 Codex 的私有隧道登录任务，修复导出图标题和长标题换行，修复矩阵工程快照兼容性，并让工作表错误及拟合说明准确反映请求。Windows 任务使用当前用户权限和已有隧道，不共享连接密钥；驻留程序在连接进程意外退出后以 5/15/30 秒间隔作有限重连，连续稳定运行 5 分钟后重置次数。云端验收范围及现场恢复见 [Work 排障](docs/WORK_TROUBLESHOOTING.md)。

0.2.2 修复从完整模式切换到经济模式后，旧宿主会话缓存工具名导致的 `Unknown tool`。经济模式仍只展示 5 个入口，旧名称在服务端兼容转发并沿用完整参数、视觉能力和会话校验。见 [Work 排障](docs/WORK_TROUBLESHOOTING.md)。

0.2.6 增加云端 CSV/TSV 文本直接导入和 Beer–Lambert 简化配方；失败作业明确停止轮询并提供恢复提示。常规拟合复用已验证的 Origin 原生流程，无需临时 Python 或 NumPy。经济模式仍显示 5 个入口，完整操作增至 14 个。


0.2.7 adds verified binary downloads over the existing private MCP connection. Cloud hosts that expose an embedded resource without creating a file can request the built-in receiver on demand; it saves bytes in the host output directory and verifies SHA256 without browser globals or a persistent terminal. Numeric Unicode superscripts/subscripts in graph titles and axes use Origin rich text, avoiding missing-glyph boxes. The core still advertises five economy tools, with no added runtime dependency or model API. See [file delivery](skills/origin-workflow/references/FILE_DELIVERY.md).
