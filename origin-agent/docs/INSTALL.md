# Install Origin Companion 0.2.9

Supported baseline: **Origin 2026 SR1 (10.300197)** or **Origin 2026b SR2 (10.350243)**, Windows x64, standard Origin edition, activated and non-Demo. Install and activate one of these builds on each computer first. SR2 has recorded native and cloud acceptance; SR1 has second-device native and Terra max cloud execution evidence, with delivery details and a tool-host startup issue still open. Version detection alone is not acceptance. The plugin does not distribute Origin or university licences, or unlock OriginPro/third-party App features.

## Choose your agent environment

Codex is used to develop and maintain this project. Students and staff install the packaged runtime and connect from cloud Work, local Work, Claude Desktop, WorkBuddy or another supported agent. No source checkout, Git, code project or separate Python installation is required. If the host asks for a folder, use your research materials folder.

| Environment | Connection and evidence |
| --- | --- |
| Chat, cloud Work and Codex | Choose `openai` and use **Connect-OpenAI.cmd** to reuse one registered Origin Companion. Actual connection tests passed in all three surfaces. Initial tunnel/account setup remains separate. |
| Local Work | The same registered entry is intended for local Work. Actual desktop attempts are currently blocked by the host project-sync error described in [UNIFIED_PLUGIN.md](UNIFIED_PLUGIN.md); Codex and browser Work do not certify this surface. |
| Claude Desktop / WorkBuddy | Use the matching installer options below. Local configuration and protocol have been checked; actual host/model workflows are recorded separately. |

Once connected, describe the analysis, figure or project edit and review returned images and editable projects. Maintenance commands below are for troubleshooting or advanced setup, not every use.

See [One Origin Companion](UNIFIED_PLUGIN.md) for the single-entry design, safe consolidation and rollback. The older `codex` installer choice now means the unified OpenAI route. `codex-direct` is an optional advanced local MCP adapter; it is not needed alongside the registered app.

## Download, extract and install

1. Get `origin-agent-0.2.9-windows-x64.zip` from the [release page](https://github.com/saigyujikingyo-png/origin-agent-bridge/releases/tag/v0.2.9), check the supplied SHA-256 and extract to an ordinary local folder.
2. Double-click `Install.cmd`. Enter `openai` for Chat/Work/Codex, or other hosts such as `claude,workbuddy`. Pressing Enter installs the engine only. The OpenAI option opens the account-link window after installation. Reuse the existing private connection; first-time users still complete the secure-connection steps below.
3. The installer verifies the complete file set, copies the bundled runtime, starts Origin with synthetic data and checks the build and numerical read-back. It merges host configuration and switches the active version only after these checks pass. Reopen the selected agent.
4. Ask the agent to check Origin Companion status before submitting a real analysis, plotting or editing task.

There is no separate Python, Node, uv or compiler requirement. The default runtime is `%USERPROFILE%\.origin-agent\app\0.2.9`; research outputs and sessions live under `%USERPROFILE%\.origin-agent`. Origin installation/licensing is unchanged. The engine installation does not register startup by default; cloud users can enable the private-tunnel login task below. Packages do not have a commercial code signature: a hash verifies transfer integrity, not publisher identity.

For an unattended upgrade of an existing installation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1 -NonInteractive -Hosts claude,workbuddy
```

The installer preserves other MCP/host settings, old runtime versions and research data. Each installation returns a `receipt_id`, with backups under `.origin-agent\installations\<receipt_id>`. A failed upgrade restores modified configuration automatically; if the user has subsequently edited a file, rollback reports the conflict and preserves that edit. To request rollback:

```powershell
& "$env:USERPROFILE\.origin-agent\app\0.2.9\server\origin-agent.exe" rollback-install <receipt_id>
```

Native diagnostics:

```powershell
& "$env:USERPROFILE\.origin-agent\app\0.2.9\server\origin-agent.exe" doctor --native
```

`doctor` alone checks discovery; `--native` creates a synthetic project and verifies native read-back. Finish or roll back an open GUI transaction before installation. GUI interaction needs an unlocked interactive Windows desktop. Sleep, closing the lid or shutdown can interrupt local jobs; read job/session status before resuming.

## Host options

- **Claude Desktop:** select `claude` to merge configuration automatically, or import the `.mcpb` directly. It includes its runtime and uses the default local data directory. Automatic skill loading depends on the host; compact tool guidance is also served by the plugin.
- **WorkBuddy:** select `workbuddy` to merge `~/.workbuddy/mcp.json` and install the workflow skill. The package's `workbuddy` folder includes connector metadata and the blue open-circle icon.
- **Local Work:** this is a separate user entrypoint requiring acceptance. Codex development setup is not a substitute for its installation instructions.
- **Other MCP agents:** use `.origin-agent/host-configs/0.2.9/generic-mcp.json` through the host's supported configuration flow. Hosts have different connection/plugin formats but share the runtime and workflow contract; actual host acceptance is still needed.

<details>
<summary>Development and optional compatibility: Codex / Claude Code</summary>

- **Codex:** the recommended `openai` setup uses the same registered connection as Chat and Work. The legacy `codex` selection routes to that setup. Advanced offline users can deliberately choose `codex-direct` for a local MCP command; enabling both routes is outside the single-entry setup. See [UNIFIED_PLUGIN.md](UNIFIED_PLUGIN.md).
- **Claude Code:** the packaged `.claude-plugin`, `plugin.json` and `skills` can be used for development, debugging or optional compatibility.

</details>

Full mode exposes 14 tools; economy mode exposes five, with additional operation arguments retrieved on demand. Both use the same Origin core. Tool count is not function coverage; see [COVERAGE.md](COVERAGE.md).

## ChatGPT cloud connection

The installer does not reset an existing tunnel, account association or key. Reconnect after an upgrade to launch the new runtime. For first-time setup, follow the [official Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) using a supported account, your own workspace, Tunnel ID and locally configured key:

```powershell
.\Connect-ChatGPT.ps1 -TunnelId <your-tunnel-id> -TunnelClient <official-client-path> -Run
```

When creating the personal ChatGPT entry, upload [`assets/icon-chatgpt.png`](../assets/icon-chatgpt.png) in the optional icon field before saving. It is the blue open-circle design at 256 x 256 pixels and under 10 KB. The larger local icon and MCP icon metadata do not set the remote listing artwork. For an existing entry without an icon editor, see the [replacement guidance](UNIFIED_PLUGIN.md#registered-chatgpt-icon). The small PNG is provided separately with the 0.2.9 release; previously published ZIP/MCPB archives are unchanged.

Keep the key on your computer, not in source or chat. Existing users reconnect with their own launcher; do not share the developer's tunnel configuration, account or key. The Windows computer must be on and the tunnel client online. Chat attachments do not automatically appear on Windows; the agent needs a local copy or a supported transfer route before using them.

### Run the cloud connection independently of Codex

If your private tunnel is configured and a suitably restricted key is stored at `.origin-agent/secrets/tunnel-key.dpapi`, run the script beside the release package:

```powershell
.\Enable-ChatGPT-Tunnel-Startup.ps1 -StartNow
```

This creates a current-user Windows login task whose name begins with `Origin Companion Private Tunnel`. New tasks include the current user's SID to avoid name collisions; existing personal tasks keep their names. The task runs with normal user permissions in a hidden window while the user is logged in, independently of Codex. The wrapper reads the active installation pointer. The tunnel client handles network reconnection; if the process exits unexpectedly, Task Scheduler retries up to three times at one-minute intervals. It does not run Origin during logout, shutdown or sleep, or replace the unlocked desktop required for GUI interaction.

Connection profiles live at `%USERPROFILE%\.origin-agent\cloud\profiles`. Initial setup copies the user's existing connection configuration, retaining environment-variable references for keys; it does not create or copy another person's credentials. This avoids AppData redirection in MSIX-packaged applications. The background process decrypts the key for the current user only; it is not written to arguments, the repository or shared packages. A missing encrypted key is reported as a setup prerequisite, with no hidden background input prompt.

Check the scheduled task, `tunnel-client runtimes status origin-agent --json`, and an actual `origin_status` call in Work. A running process alone does not prove cloud connectivity. `.origin-agent/cloud/background-status.json` and `background-error.json` retain the latest success/error timestamps; an old error does not establish a current failure.

To disable it, stop and disable your own scheduled task, then run `tunnel-client runtimes stop origin-agent` for the same alias. Re-enable using the same setup script. Closing Codex alone is insufficient; do not terminate unrelated Origin instances. This does not change model subscriptions or university licensing.

The bridge is MIT-licensed and adds no paid model intermediary. Origin, agent hosts and cloud services remain subject to their respective licences/plans; check the provider's current terms for account availability and pricing.

## Updates and result delivery

After updating, reconnect the local plugin or refresh the cloud connection's tool list, then start a new conversation if the old one retains cached tools. The installed runtime and actual Chat, cloud Work and fresh Codex calls returned 0.2.9; see the [current acceptance record](https://github.com/saigyujikingyo-png/origin-agent-bridge/blob/codex/origin-companion-release/WORK_ACCEPTANCE_0.2.9.md). Local Work remains separately blocked by host project synchronisation.

Save results to your Downloads folder or another chosen authorised location. University OneDrive is not required. Native execution, host file receipt and a particular browser's automated download route are separate checks. See [Work troubleshooting](WORK_TROUBLESHOOTING.md).

## Multiple computers and removal

Install the same ZIP independently on each supported Windows computer so local absolute paths are generated correctly. Do not copy another computer's generated host JSON. Each person uses their own Origin licence and agent account. Portable installation mechanisms and actual second-device acceptance are distinct; see [VALIDATION.md](VALIDATION.md).

To remove the plugin, first remove its host/plugin connection or roll back the installation configuration, then remove the runtime version directory. Personal OPJU files, data and sessions may be retained. General Python/LabTalk/Origin C code runs with the current Windows user's permissions; the worker process is not a script security sandbox.

See [MODELS.md](MODELS.md) for model/economy profiles and [ELM.md](ELM.md) for university model-service evidence.
