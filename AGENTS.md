# Chembridge / Origin Companion

Read DEVELOPMENT_PRINCIPLES.md before planning, implementing, testing, or releasing. It contains the user's shared Chembridge requirements and applies to this entire repository. Read CHEMBRIDGE.md for scope and CLOUD_STORAGE.md for storage; retain plugin-specific requirements and evidence boundaries.

Shared defaults: public GitHub open-source distribution with an explicit licence, English public documentation and release notes; simple installation for non-developers; multiple general Agent hosts and model capabilities; GPT-5.6 Terra with max reasoning as the default benchmark; verified University of Edinburgh requirements; lightweight, responsive execution and efficient use of model quota. Do not make users repeat these decisions in each development task.

The target is one plugin identity and shared execution core for ChatGPT Chat, local Work, cloud Work, Codex, Claude, WorkBuddy and other suitable Agent hosts. Codex is both a development tool and an end-user host; ordinary plugin use must not require a source checkout or coding project. Target support and actual acceptance are separate. Do not claim all functions, hosts or models are verified from protocol tests alone.

The private university OneDrive is for development archives, not a required runtime or result destination. Deliver artifacts to the user's chosen authorized location. Distinguish native execution, host attachment delivery and automated browser downloads; a policy-blocked download route is not an Origin execution failure.

This repository implements Origin Companion; its Python package is origin-agent. Run commands from this checkout, with package commands under origin-agent when required. Machine-local runtime data and credentials stay outside the repository and cloud-sync working files. Preserve unrelated changes and existing working state.

For any new Chembridge plugin created in a separate checkout, carry the current shared principles into that checkout and add an AGENTS.md entry requiring them. Keep the shared rule version and product-specific acceptance records clear. User instructions take precedence.

## Confirmed external host issue

The user confirmed the OpenAI local Work project-synchronisation problem as an OpenAI frontend bug and instructed us to stop attempting repairs. Do not resume investigation, cache manipulation or host patching for that issue unless the user explicitly reopens it. Record it as an external limitation; do not infer that the affected host passed. For the next plugin, read ORIGIN_DEVELOPMENT_RETROSPECTIVE.md and NEXT_PLUGIN_ASSESSMENT.md.

## Independent development tasks

Origin and ChemDraw development tasks are independent. Keep implementation, progress and acceptance in their respective tasks; do not automatically relay reports or coordination messages between them.

## Codex cloud development

The whole Chembridge initiative starts at https://github.com/saigyujikingyo-png/chembridge. Its **Chembridge** cloud environment handles shared planning and new plugins; this repository uses **Chembridge / Origin Companion**. Keep product repositories and dependencies separate.

Read origin-agent/docs/CODEX_CLOUD.md for the cloud development environment. Use `bash origin-agent/scripts/setup_codex_cloud.sh` from the repository root for setup and cached-container maintenance. Run portable checks in origin-agent. Cloud container checks do not replace licensed Windows Origin execution or native and host acceptance.
