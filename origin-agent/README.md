# Origin Companion

<img src="assets/icon.svg" alt="Origin Companion" width="80" height="80">

Your agent, your Origin. Independent personal project; not an official OriginLab or university product.

The target is a smooth Origin plugin for licensed University of Edinburgh staff and students. See the [Edinburgh product definition and reuse assessment](docs/EDINBURGH_PRODUCT.md). Version 0.2 includes native programming, live projects, GUI input and a self-contained Windows installer. Coverage is recorded by verified example, not by assuming that every function works.

Agent-neutral, local Origin workflows over MCP. The personal sharing build targets the user's Edinburgh-licensed **Origin 2026b SR2 (10.350243), Windows x64, Origin edition**. Native workers check this exact baseline. This project does not distribute Origin or a licence.

Version 0.2 adds general Python/originpro/COM, LabTalk/X-Function and Origin C execution, installed capability discovery, persistent managed sessions and a native GUI transaction channel. Twelve MCP tools cover workflows, capabilities, session/GUI control and artifacts without registering one tool per Origin function. Programs run as trusted code with the Windows user's permissions.

The fixed workflow route remains available for CSV/TSV/XLSX import, multi-Y plotting, error bars, linear regression and Beer–Lambert calibration with independent numerical checks. Independent programs reopen their saved OPJU for structural verification; session programs preserve the live project and report that no reopen check occurred. Session revisions reject stale edits and failed operations restore project checkpoints. Execution checks do not establish scientific correctness.

The product target is access to the complete functionality of the user's licensed Origin edition. **Full GUI coverage and universal function validation are not complete.** See [FULL_ORIGIN.md](docs/FULL_ORIGIN.md) for the implementation contract and remaining work.

Use the installation packages described in [INSTALL.md](docs/INSTALL.md). Developers: `uv sync --locked`, then `uv run origin-agent serve`. A model-provider API key is not required by this bridge. ChatGPT cloud access uses a separately configured secure tunnel or authenticated gateway.

Source layout and performance decisions: [ARCHITECTURE.md](docs/ARCHITECTURE.md). Current measured evidence and limitations: [VALIDATION.md](docs/VALIDATION.md).

The phases and acceptance gates are in [ROADMAP.md](docs/ROADMAP.md), with module design in [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md). Persistent sessions and [GUI transactions](docs/GUI.md), including UIA, mouse, keyboard and Unicode input, have passed recorded native cases. Query `origin_capabilities("coverage")` for the [coverage matrix](docs/COVERAGE.md). The stable internal ID `origin-agent` preserves existing MCP connections; the display name and blue open-circle icon are Origin Companion.

Try a complete natural-language workflow using the [synthetic example](examples/README.md).

## 多模型与经济模式（0.2.1）

[多模型配置](docs/MODELS.md)支持 DeepSeek、GPT Terra、Gemini、GLM、Kimi 与 ELM 宿主预设。5 工具经济接口按需加载全部操作参数，常见配方使用短参数，文本输出可分页；完整 13 工具接口仍可选择。[ELM 提供的模型与额度边界](docs/ELM.md)。预设适配不是实际模型成功率认证，插件不额外调用模型 API。
