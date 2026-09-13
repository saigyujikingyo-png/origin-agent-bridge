# Origin Companion

<img src="origin-agent/assets/icon.svg" alt="Origin Companion blue open-circle icon" width="80" height="80">

**Your agent, your Origin.** Use natural language to import data, fit models, create figures and edit native Origin projects through a general-purpose agent.

Origin Companion is part of [Chembridge](CHEMBRIDGE.md), a collection of plugins for University of Edinburgh students, staff and researchers. It is an independent project, not an official university or OriginLab product.

**Open-source, unified-agent target:** use the same Origin Companion in ChatGPT Chat, local Work, cloud Work, Codex and other suitable agents, backed by one execution core and thin host adapters. Actual acceptance for each entrypoint is recorded below.

## Download and start

**[Download the 0.2.9 Windows preview](https://github.com/saigyujikingyo-png/origin-agent-bridge/releases/tag/v0.2.9)**

1. Download the Windows x64 ZIP, extract it and double-click `Install.cmd`.
2. For Chat, Work and Codex, use **Connect-OpenAI.cmd** to reuse one registered Origin Companion. Connect other agents using the [installation guide](origin-agent/docs/INSTALL.md). The installer includes its runtime; you do not need Git, Python or a development environment. First-time cloud connections still require account-specific setup.
3. Provide your data and describe the analysis or figure you need. Start with the [synthetic calibration example](origin-agent/examples/README.md).
4. Review the results and collect PNG, PDF, SVG and editable OPJU files in your chosen location. Your Downloads folder is suitable; university OneDrive is not required.

Each Windows computer needs its own valid, activated **Origin 2026 SR1 (10.300197)** or **Origin 2026b SR2 (10.350243)**, x64, standard Origin edition. The plugin does not include Origin or a university licence, or unlock OriginPro and third-party App features.

## What it can do

- Import and inspect CSV, TSV and XLSX data; plot multiple series and supplied error bars.
- Run linear regression and Beer–Lambert calibration with explicit intercept and weighting choices, plus independent numerical checks.
- Use native Python, LabTalk, X-Functions and Origin C for broader analysis and editing tasks.
- Continue working in managed Origin sessions, save checkpoints and recover project changes.
- Use GUI controls when a task needs interaction beyond the native programming interfaces.
- Return figures and native editable projects with verification records.

Five compact tools, on-demand help and batch workflows make the interface suitable for economical models. **GPT-5.6 Terra with max reasoning** is the project's benchmark. Model presets also cover DeepSeek, Gemini, GLM, Kimi and ELM, but presets do not certify real model performance. See [model support and efficiency](origin-agent/docs/MODELS.md).

## Compatibility and current evidence

| Environment | Recorded result | Remaining limits |
| --- | --- | --- |
| Origin 2026b SR2 | Native acceptance cases and actual cloud Work receipt of PNG, PDF, SVG and OPJU | Every Origin function and App has not been verified |
| Origin 2026 SR1, second device | Four NIST native datasets; Terra max cloud Work Norris fit and OPJU reopen | Complete independent receipt details for all four cloud artifacts and the original tool-host launch context remain unresolved |
| Chat, cloud Work and Codex | Same registered app passed status/help in all three; Work/Codex used Terra max | Connection acceptance is separate from each complete scientific workflow |
| Local Work desktop UI | Attempts blocked before Origin by the desktop project-sync error | This host issue remains unresolved on the tested session; see the 0.2.9 report |
| Claude Desktop, WorkBuddy and other agents | Shared runtime, host configuration and protocol checks | Each actual host/model workflow requires its own acceptance |

**0.2.9 is a preview, not a claim of complete Origin coverage or universal host compatibility.** The user confirmed a download to their own Downloads folder, but did not supply the device, full file list or hashes for that follow-up. See the [0.2.8 acceptance report](WORK_ACCEPTANCE_0.2.8.md) and [coverage matrix](origin-agent/docs/COVERAGE.md).

## Guides and evidence

- [One plugin across OpenAI surfaces](origin-agent/docs/UNIFIED_PLUGIN.md) and [0.2.9 acceptance](WORK_ACCEPTANCE_0.2.9.md)
- [Installation, connection, updates and recovery](origin-agent/docs/INSTALL.md)
- [Troubleshooting cloud Work](origin-agent/docs/WORK_TROUBLESHOOTING.md)
- [Product scope and acceptance criteria](origin-agent/docs/EDINBURGH_PRODUCT.md)
- [Roadmap](origin-agent/docs/ROADMAP.md)
- [Native NIST verification](NIST_ACCEPTANCE_2026-09-12.md)
- [Earlier Work acceptance](WORK_ACCEPTANCE_2026-09-11.md), [workflow recovery](WORK_RECOVERY_0.2.6.md) and [file delivery](WORK_DELIVERY_0.2.7.md)
- [Developer guide](origin-agent/README.md) and [architecture](origin-agent/docs/ARCHITECTURE.md)
- [Shared Chembridge principles](DEVELOPMENT_PRINCIPLES.md), [GitHub distribution](PUBLIC_DISTRIBUTION.md) and [development storage](CLOUD_STORAGE.md)

Codex is both an end-user agent host and a tool for developing and maintaining the plugin. Users work in their chosen agent environment; a source checkout or code project is not a runtime requirement. Public GitHub documentation is in English; natural-language requests can still be made in other languages supported by the selected agent.

Plugin source is public and licensed under [MIT](LICENSE). Third-party libraries retain their own licences; Origin software and licences are not redistributed.
