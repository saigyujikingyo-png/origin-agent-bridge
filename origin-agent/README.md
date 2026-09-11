# Origin Companion

<img src="assets/icon.svg" alt="Origin Companion" width="80" height="80">

Your agent, your Origin. Independent personal project; not an official OriginLab or university product.

The current development target is a smooth, complete Origin plugin for licensed University of Edinburgh staff and students. See the [Edinburgh product definition and reuse assessment](docs/EDINBURGH_PRODUCT.md). Version 0.2 is an unreleased engineering prototype; the installed/released 0.1 version has narrower capabilities.

Agent-neutral, local Origin workflows over MCP. The personal sharing build targets the user's Edinburgh-licensed **Origin 2026b SR2 (10.350243), Windows x64, Origin edition**. Native workers check this exact baseline. This project does not distribute Origin or a licence.

Version 0.2 adds general Python/originpro/COM, LabTalk/X-Function and Origin C execution, installed capability discovery, persistent managed sessions and a native GUI transaction channel. Twelve MCP tools cover workflows, capabilities, session/GUI control and artifacts without registering one tool per Origin function. Programs run as trusted code with the Windows user's permissions.

The fixed workflow route remains available for CSV/TSV/XLSX import, multi-Y plotting, error bars, linear regression and Beer–Lambert calibration with independent numerical checks. Independent programs reopen their saved OPJU for structural verification; session programs preserve the live project and report that no reopen check occurred. Session revisions reject stale edits and failed operations restore project checkpoints. Execution checks do not establish scientific correctness.

The product target is access to the complete functionality of the user's licensed Origin edition. **Full GUI coverage and universal function validation are not complete.** See [FULL_ORIGIN.md](docs/FULL_ORIGIN.md) for the implementation contract and remaining work.

Use the installation packages described in [INSTALL.md](docs/INSTALL.md). Developers: `uv sync --locked`, then `uv run origin-agent serve`. A model-provider API key is not required by this bridge. ChatGPT cloud access uses a separately configured secure tunnel or authenticated gateway.

Source layout and performance decisions: [ARCHITECTURE.md](docs/ARCHITECTURE.md). Current measured evidence and limitations: [VALIDATION.md](docs/VALIDATION.md).

The phases and acceptance gates are in [ROADMAP.md](docs/ROADMAP.md), with module design in [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md). Persistent sessions and the [basic GUI transaction channel](docs/GUI.md) have passed recorded native cases. Complex controls and full-function acceptance remain pending. The stable internal ID `origin-agent` preserves existing MCP connections; the display name and blue open-circle icon are Origin Companion.

Try a complete natural-language workflow using the [synthetic example](examples/README.md).
