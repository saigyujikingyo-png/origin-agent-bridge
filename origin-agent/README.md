# Origin Agent Bridge

Agent-neutral, local Origin workflows over MCP. Windows x64 + an activated Origin 2021 or later are required for native execution. This project does not distribute Origin or a licence.

The current core imports CSV/TSV/XLSX values, plots multiple Y series with optional error bars, performs native linear regression and Beer–Lambert calibration, exports editable OPJU/PNG/PDF/SVG, and verifies the saved project by reopening it in Origin.

Use the installation packages described in [INSTALL.md](docs/INSTALL.md). Developers: `uv sync --locked`, then `uv run origin-agent serve`. A model-provider API key is not required by this bridge. ChatGPT cloud access uses a separately configured secure tunnel or authenticated gateway.

Source layout and performance decisions: [ARCHITECTURE.md](docs/ARCHITECTURE.md). Current measured evidence and limitations: [VALIDATION.md](docs/VALIDATION.md).
