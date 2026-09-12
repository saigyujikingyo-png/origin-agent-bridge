# Chembridge

Chembridge develops plugins and agent workflows that make study, research and everyday university work easier for University of Edinburgh students and staff. It is an umbrella project; Origin Companion is one of its specialist software plugins.

| Area | User goal | Deliverable |
| --- | --- | --- |
| University convenience plugins | Find and organise materials; reuse common university workflows | Plugins connected to sources authorised by the user |
| Specialist software plugins | Use licensed software through natural language while retaining editable native results | General-purpose agent interfaces and any necessary local execution runtime |
| Workflow automation plugins | Connect retrieval, processing, software execution, checking and delivery | Traceable workflows with recovery mechanisms |

These areas define the scope, not a list of completed products. This repository delivers Origin Companion and retains its name, packages, release history and GitHub address. Add separate modules or repositories as products mature; do not build a large platform before it is needed.

## Shared principles

Read the [Chembridge development and delivery principles](DEVELOPMENT_PRINCIPLES.md), version **2026-09-12.4**, before development. The defaults are GitHub distribution in English, accessible installation for non-developers, multiple agents and models, economical-model support, **GPT-5.6 Terra + max as the benchmark**, verified task-specific Edinburgh requirements, and lightweight, responsive, efficient operation with careful use of model quota. Record evidence, compatibility and remaining work separately; these goals are not all certified achievements.

Each new plugin must reference these principles in its own `AGENTS.md`, so users do not need to repeat them in every development task. New user instructions take precedence. Tasks already running must reread the entrypoint to adopt updated rules.

## Use and development

Users describe goals, provide necessary materials and review results in cloud or local Work, Claude, WorkBuddy or another agent environment. Codex is used for development, maintenance and acceptance. A code checkout, Git and a development terminal should not be prerequisites for using a plugin.

Plugins share a small set of conventions: check capabilities and the target device, load operation guidance on demand, batch execution, return job status and actionable errors, and deliver artifacts with verification records. Specialist software runs on each user's legally licensed execution device. Accounts, licences and connection credentials remain individual.

Prefer existing MCP implementations, official software APIs and portable formats. Add GUI adapters only where needed. Do not introduce extra model services, database clusters or persistent development servers by default. Extract common mechanisms after demonstrated reuse, rather than creating a large general framework in advance.

## Delivery and acceptance

Each plugin records its own version, host, target software, device and verified cases. Protocol tests, native scripts and CI cannot replace acceptance through the actual agent work environment. Arbitrary script execution does not prove complete function coverage; results from one device or software version do not certify another.

GitHub holds source, documentation, public tests and releases. Large development datasets and historical materials follow the [cloud storage policy](CLOUD_STORAGE.md); local storage holds the active working set and runtime essentials. Open source does not make private data or restricted university materials public.

The university cloud folder is a development archive, not a required destination for plugin results. Deliver to the user's chosen location. Assess automated browser download restrictions separately from native execution and host file delivery.

## Preparation for the next plugin

- [Origin development retrospective](ORIGIN_DEVELOPMENT_RETROSPECTIVE.md): native execution, output quality, host delivery and lightweight implementation lessons.
- [ChemDraw versus Mnova assessment](NEXT_PLUGIN_ASSESSMENT.md): current evidence, native feasibility gates and the recommended development sequence. ChemAIst remains an unaccepted prototype for the required drawing quality; it is not evidence that ChemDraw automation is complete.

## Current module

- [Origin Companion](README.md): natural-language analysis, plotting and project editing for Origin 2026 SR1 and 2026b SR2.
- [Origin product scope and acceptance criteria](origin-agent/docs/EDINBURGH_PRODUCT.md)
- [Development roadmap](origin-agent/docs/ROADMAP.md)
