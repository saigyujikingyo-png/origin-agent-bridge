# Chembridge / Origin Companion

Read DEVELOPMENT_PRINCIPLES.md before planning, implementing, testing, or releasing. It contains the user's shared Chembridge requirements and applies to this entire repository. Read CHEMBRIDGE.md for scope and CLOUD_STORAGE.md for storage; retain plugin-specific requirements and evidence boundaries.

Shared defaults: GitHub distribution; simple installation for non-developers; multiple general Agent hosts and model capabilities; GPT-5.6 Terra with max reasoning as the default benchmark; verified University of Edinburgh requirements; lightweight, responsive execution and efficient use of model quota. Do not make users repeat these decisions in each development task.

Codex is the development environment. Users run plugins in Work cloud/local, Claude, WorkBuddy and other supported general Agent work environments. Target support and actual acceptance are separate. Do not claim all functions, hosts or models are verified from protocol tests alone.

This repository implements Origin Companion; its Python package is origin-agent. Run commands from this checkout, with package commands under origin-agent when required. Machine-local runtime data and credentials stay outside the repository and cloud-sync working files. Preserve unrelated changes and existing working state.

For any new Chembridge plugin created in a separate checkout, carry the current shared principles into that checkout and add an AGENTS.md entry requiring them. Keep the shared rule version and product-specific acceptance records clear. User instructions take precedence.
