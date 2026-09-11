# Origin Agent Bridge

The current development target is a smooth, complete Origin plugin for licensed University of Edinburgh staff and students. See the [Edinburgh product definition and reuse assessment](docs/EDINBURGH_PRODUCT.md). Version 0.2 is an unreleased engineering prototype; the installed/released 0.1 version has narrower capabilities.

Agent-neutral, local Origin workflows over MCP. The personal sharing build targets the user's Edinburgh-licensed **Origin 2026b SR2 (10.350243), Windows x64, Origin edition**. Native workers check this exact baseline. This project does not distribute Origin or a licence.

Version 0.2 adds general Python/originpro/COM, LabTalk/X-Function and Origin C execution, installed capability discovery, and editing copies of existing OPJ/OPJU projects. Two coarse tools expose these interfaces without registering a tool for every Origin function. Programs run as trusted code with the Windows user's permissions.

The fixed workflow route remains available for CSV/TSV/XLSX import, multi-Y plotting, error bars, linear regression and Beer–Lambert calibration with independent numerical checks. General programs produce reopened OPJU projects, requested graphs, scripts, results and verification records; execution and structural checks do not establish scientific correctness.

The product target is access to the complete functionality of the user's licensed Origin edition. **Full GUI coverage and universal function validation are not complete.** See [FULL_ORIGIN.md](docs/FULL_ORIGIN.md) for the implementation contract and remaining work.

Use the installation packages described in [INSTALL.md](docs/INSTALL.md). Developers: `uv sync --locked`, then `uv run origin-agent serve`. A model-provider API key is not required by this bridge. ChatGPT cloud access uses a separately configured secure tunnel or authenticated gateway.

Source layout and performance decisions: [ARCHITECTURE.md](docs/ARCHITECTURE.md). Current measured evidence and limitations: [VALIDATION.md](docs/VALIDATION.md).

Try a complete natural-language workflow using the [synthetic example](examples/README.md).
