# Codex Web development environment

This environment provides cloud code development, linting and portable tests for Origin Companion. It is separate from using the installed plugin in Chat, Work or Codex. Native Origin execution and native acceptance require the configured, licensed Windows executor.

## Configure the environment

1. Open [Codex cloud environment settings](https://chatgpt.com/codex/cloud/settings/environments). Reuse the existing GitHub connection and authorise this repository if it is not listed. Complete any GitHub account verification in the browser; no new OpenAI API key is required for this configuration.
2. Select `saigyujikingyo-png/origin-agent-bridge`. Use the current repository default branch, `codex/origin-companion-release`, unless a task specifies another branch.
3. Name the environment **Origin Companion** and select the **universal** container image.
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

Official references: [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment) and [internet access](https://learn.chatgpt.com/docs/cloud/internet-access).
