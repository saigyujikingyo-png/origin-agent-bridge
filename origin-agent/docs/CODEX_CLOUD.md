# Codex Web development environment

This environment provides cloud code development, linting and portable tests for Origin Companion. It is separate from using the installed plugin in Chat, Work or Codex. Native Origin execution and native acceptance require the configured, licensed Windows executor.

The shared entrypoint for the whole initiative is the [Chembridge hub](https://github.com/saigyujikingyo-png/chembridge). Use its **Chembridge** environment for cross-project standards and new-plugin planning, and **Chembridge / Origin Companion** for this product.

## Configure the environment

1. Open [Codex cloud environment settings](https://chatgpt.com/codex/cloud/settings/environments). Reuse the existing GitHub connection and authorise this repository if it is not listed. Complete any GitHub account verification in the browser; no new OpenAI API key is required for this configuration.
2. Select `saigyujikingyo-png/origin-agent-bridge`. Use the current repository default branch, `codex/origin-companion-release`, unless a task specifies another branch.
3. Name the environment **Chembridge / Origin Companion** and select the **universal** container image.
4. Keep container caching enabled. Choose manual setup and enter the following as both the setup and maintenance script:

   ```bash
   bash origin-agent/scripts/setup_codex_cloud.sh
   ```

   The script resolves the package directory from its own location and installs the locked Python 3.12 environment. It requires `uv`; the script reports a clear error if the selected image does not provide it. Reusing the same script refreshes dependencies after a branch or lockfile change without creating a second environment.
5. No project secrets are needed for portable checks. Keep Origin licences, tunnel credentials, private research data and machine-local configuration outside this cloud development environment.
6. Use the interactive terminal to run the checks below, then save the environment. Select this environment for subsequent cloud tasks.

## Verify cloud execution

From the checked-out repository root:

```bash
cd origin-agent
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

Record the actual commit, container platform, Python version and command results. A successful dependency install is not a passed test suite. Portable tests do not establish native Origin, GUI, model, or end-user artifact-delivery acceptance.

The setup stage can download dependencies even when agent internet access is disabled. Enable only the network access needed by a task through the official environment settings; do not work around account or network policies. Cloud execution does not automatically remove local checkouts or caches.

If the desktop cloud entry remains unavailable after the environment is saved, check that the same account and repository are selected. The separately confirmed local Work project-sync frontend issue is outside this environment configuration and must not be treated as an Origin failure or repaired here.

## Verified configuration: 13 September 2026

The environment was initially saved as **Origin Companion**, and the Codex Web cloud task composer showed it as selected. It was subsequently renamed and saved as **Chembridge / Origin Companion** when the whole Chembridge workspace was configured; the environment identity and setup were reused. The existing GitHub connection was reused; no new API keys or project secrets were added.

| Check | Observed result |
| --- | --- |
| Repository and tested commit | `saigyujikingyo-png/origin-agent-bridge`, `d536599b7e90cbfa42f8c60cc94446dfbf447964` |
| Container | `universal`, Ubuntu 24.04-based Linux image |
| Python | `3.12.13` |
| Initial setup | Passed; 39 packages prepared in 1.93 seconds and installed in 30 milliseconds |
| Maintenance script | Passed; the same lockfile was resolved and 39 packages audited in 0.77 milliseconds |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 81 files already formatted |
| `uv run pytest -q` | **175 passed in 19.52 seconds** |
| Environment save and selection | Saved successfully; selected in the cloud task composer |

Container caching is enabled. Agent internet access is configured with the common-dependencies allowlist and `GET`, `HEAD`, and `OPTIONS`. Additional allowed domains are `originlab.com`, `www.originlab.com`, `developers.openai.com`, `learn.chatgpt.com`, `docs.astral.sh`, and `modelcontextprotocol.io`.

Package timings above cover the reported `uv` phases, not complete cold-container startup or billed model usage. The verification ran in the environment's interactive terminal. It did not run a model-based cloud task, verify the desktop cloud-dispatch menu, or execute native Origin. Those are separate acceptance checks. This documentation-only receipt was added after verification; runtime code and the 0.2.9 release were unchanged.

Official references: [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment) and [internet access](https://learn.chatgpt.com/docs/cloud/internet-access).
