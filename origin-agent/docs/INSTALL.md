# Install Origin Companion 0.2.12

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

1. Get `origin-agent-0.2.12-windows-x64.zip` from the [release page](https://github.com/saigyujikingyo-png/origin-agent-bridge/releases/tag/v0.2.12), check the supplied SHA-256 and extract to an ordinary local folder.
2. Double-click `Install.cmd`. Enter `openai` for Chat/Work/Codex, or other hosts such as `claude,workbuddy`. Pressing Enter installs the engine only. The OpenAI option opens the account-link window after installation. Reuse the existing private connection; first-time users still complete the secure-connection steps below.
3. The installer verifies the complete file set, copies the bundled runtime, starts Origin with synthetic data and checks the build and numerical read-back. It merges host configuration and switches the active version only after these checks pass. Reopen the selected agent.
4. Ask the agent to check Origin Companion status before submitting a real analysis, plotting or editing task.

There is no separate Python, Node, uv or compiler requirement. The default runtime is `%USERPROFILE%\.origin-agent\app\0.2.12`; research outputs and sessions live under `%USERPROFILE%\.origin-agent`. Origin installation/licensing is unchanged. The engine installation does not register startup by default; cloud users can enable the private-tunnel login task below. Packages do not have a commercial code signature: a hash verifies transfer integrity, not publisher identity.

For an unattended upgrade of an existing installation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1 -NonInteractive -Hosts claude,workbuddy
```

The installer preserves other MCP/host settings, old runtime versions and research data. Each installation returns a `receipt_id`, with backups under `.origin-agent\installations\<receipt_id>`. A failed upgrade restores modified configuration automatically; if the user has subsequently edited a file, rollback reports the conflict and preserves that edit. To request rollback:

```powershell
& "$env:USERPROFILE\.origin-agent\app\0.2.12\server\origin-agent.exe" rollback-install <receipt_id>
```

If an interrupted upgrade reports `lifecycle_recovery_required:<receipt_id>`, repeat the rollback command with that exact receipt. The durable transaction record prevents a new installation or connector start from entering a partly restored configuration. Do not delete the transaction record or replace it with another receipt. Recovery checks recorded file/task identity and preserves conflicting user edits for inspection.

Rollback restores old task definitions **disabled** while restoring the engine and files. Only after the rollback receipt commits does it restore the previous startup preference, with a fresh admission check and scheduler readback; it does not explicitly start a task. A concurrent stop or startup disable takes precedence. If preference restoration fails or reports pending activation, repeat the same rollback command: it resumes that recorded step without rerunning Origin or repeating a completed shutdown. A pending activation blocks a new upgrade until this recovery finishes. Restored startup settings are not proof of a live cloud connection. Older launchers restored from a previous release do not acquire the new lifecycle safeguards; keep their historical limitations in mind when choosing rollback.

Native diagnostics:

```powershell
& "$env:USERPROFILE\.origin-agent\app\0.2.12\server\origin-agent.exe" doctor --native
```

`doctor` alone checks discovery; `--native` creates a synthetic project and verifies native read-back. Finish or roll back an open GUI transaction before installation. GUI interaction needs an unlocked interactive Windows desktop. Sleep, closing the lid or shutdown can interrupt local jobs; read job/session status before resuming.

## Host options

- **Claude Desktop:** select `claude` to merge configuration automatically, or import the `.mcpb` directly. It includes its runtime and uses the default local data directory. Automatic skill loading depends on the host; compact tool guidance is also served by the plugin.
- **WorkBuddy:** select `workbuddy` to merge `~/.workbuddy/mcp.json` and install the workflow skill. The package's `workbuddy` folder includes connector metadata and the blue open-circle icon.
- **Local Work:** this is a separate user entrypoint requiring acceptance. Codex development setup is not a substitute for its installation instructions.
- **Other MCP agents:** use `.origin-agent/host-configs/0.2.12/generic-mcp.json` through the host's supported configuration flow. Hosts have different connection/plugin formats but share the runtime and workflow contract; actual host acceptance is still needed.

<details>
<summary>Development and optional compatibility: Codex / Claude Code</summary>

- **Codex:** the recommended `openai` setup uses the same registered connection as Chat and Work. The legacy `codex` selection routes to that setup. Advanced offline users can deliberately choose `codex-direct` for a local MCP command; enabling both routes is outside the single-entry setup. See [UNIFIED_PLUGIN.md](UNIFIED_PLUGIN.md).
- **Claude Code:** the packaged `.claude-plugin`, `plugin.json` and `skills` can be used for development, debugging or optional compatibility.

</details>

Full mode exposes 14 tools; economy mode exposes five, with additional operation arguments retrieved on demand. Both use the same Origin core. Tool count is not function coverage; see [COVERAGE.md](COVERAGE.md).

## ChatGPT cloud connection

The installer does not reset an existing tunnel, account association or key. It migrates every supported account's launcher and preserves startup/stop preferences. Explicitly start the connection after an upgrade. For first-time setup, follow the [official Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) using a supported account, your own workspace, Tunnel ID and locally configured key. `Connect-ChatGPT.ps1` without `-Run` initializes a new profile once and refuses to overwrite an existing identity. For an already configured account, the compatibility reconnect command is:

```powershell
.\Connect-ChatGPT.ps1 -TunnelId <your-tunnel-id> -TunnelClient <official-client-path> -Run
```

When creating the personal ChatGPT entry, upload [`assets/icon-chatgpt.png`](../assets/icon-chatgpt.png) in the optional icon field before saving. It is the blue open-circle design at 256 x 256 pixels and under 10 KB. The larger local icon and MCP icon metadata do not set the remote listing artwork. For an existing entry without an icon editor, see the [replacement guidance](UNIFIED_PLUGIN.md#registered-chatgpt-icon). The small PNG is included in the bundle and provided separately with the release.

Keep the key on your computer, not in source or chat. Existing users reconnect with their own launcher; do not share the developer's tunnel configuration, account or key. The Windows computer must be on and the tunnel client online. Chat attachments do not automatically appear on Windows; the agent needs a local copy or a supported transfer route before using them.

### Run the cloud connection independently of Codex

If your private tunnel is configured and a suitably restricted key is stored at `.origin-agent/secrets/tunnel-key.dpapi`, run the script beside the release package:

```powershell
.\Enable-ChatGPT-Tunnel-Startup.ps1 -StartNow
```

This maintains a current-user Windows login task for each configured account. Names begin with `Origin Companion Private Tunnel`; existing owned registrations retain their names. Tasks run with normal user permissions in hidden windows while the user is logged in, independently of Codex. The wrapper reads the active installation pointer. The controller checks readiness and continued health with deadlines, reconciles owned processes before retrying, and stops on ambiguous ownership. Task Scheduler has at most three one-minute restarts. This is logon startup, not pre-login boot execution; sleep, logoff and reboot recovery require separate acceptance. An unlocked desktop is still required for GUI interaction.

`-StartNow` records permission and requests a scheduler start after configuration commits. Its `start_requested` result does not establish readiness; use the status and host checks below. The advanced `tunnel disable-startup --config <account-runtime-config.json>` command records a startup-only preference without stopping an already running connector. An explicit `-StartNow` enables startup again; ordinary reinstall and rollback preserve a user disable.

The personal profile lives at `%USERPROFILE%\.origin-agent\cloud\profiles`; additional accounts use `cloud\accounts\<account>\profiles`. Each account has a generated `runtime-config.json` and the same release-owned launcher. Existing identities, environment key references and DPAPI files are reused. The background adapter decrypts the key for the current user only; it is not written to arguments, the repository or shared packages. A missing encrypted key is a setup prerequisite, with no hidden background input prompt. Do not copy someone else's account configuration.

Check the scheduled task and the engine's `tunnel status --config <account-runtime-config.json>` diagnostic, then make an actual `origin_status` call in a fresh host conversation. `supervisor-state.json` and `background-status.json` include observation time, expiry and ownership. Stale/dead observations are not success; local health does not prove account installation, fresh tool discovery or a cloud call.

To stop one account, run its installed `Stop-ChatGPT-Tunnel.ps1` beside its `runtime-config.json`, or pass the configuration with `-ConfigPath`. This records stop intent, stops only the proven connector/MCP processes, and disables its owned task. Reinstall preserves this preference. Explicit `Enable-ChatGPT-Tunnel-Startup.ps1 -StartNow` permits starting the configured connections again. Closing Codex alone is insufficient. Do not stop entire process trees or terminate unrelated Origin instances. See the [lifecycle record](RUNTIME_LIFECYCLE.md) for limits and pending OS-event acceptance.

The bridge is MIT-licensed and adds no paid model intermediary. Origin, agent hosts and cloud services remain subject to their respective licences/plans; check the provider's current terms for account availability and pricing.

## Updates and result delivery

After updating, reconnect the local plugin or refresh the cloud connection's tool list, then start a new conversation if the old one retains cached tools. The installed runtime and actual Chat, cloud Work and fresh Codex calls returned 0.2.9; see the [historical acceptance record](https://github.com/saigyujikingyo-png/origin-agent-bridge/blob/codex/origin-companion-release/WORK_ACCEPTANCE_0.2.9.md). Local Work remains separately blocked by host project synchronisation.

Save results to your Downloads folder or another chosen authorised location. University OneDrive is not required. Native execution, host file receipt and a particular browser's automated download route are separate checks. See [Work troubleshooting](WORK_TROUBLESHOOTING.md).

## Multiple computers and removal

Install the same ZIP independently on each supported Windows computer so local absolute paths are generated correctly. Do not copy another computer's generated host JSON. Each person uses their own Origin licence and agent account. Portable installation mechanisms and actual second-device acceptance are distinct; see [VALIDATION.md](VALIDATION.md).

To remove the plugin, first remove its host/plugin connection or roll back the installation configuration, then remove the runtime version directory. Personal OPJU files, data and sessions may be retained. General Python/LabTalk/Origin C code runs with the current Windows user's permissions; the worker process is not a script security sandbox.

See [MODELS.md](MODELS.md) for model/economy profiles and [ELM.md](ELM.md) for university model-service evidence.


## Upgrading to 0.2.12

Download the Windows ZIP from [GitHub Releases](https://github.com/saigyujikingyo-png/origin-agent-bridge/releases/tag/v0.2.12), verify its SHA-256, extract it and run `Install.cmd`. The installer checks native Origin before selecting the new runtime. Keep 0.2.11 for rollback. Existing data, account connections and encrypted credentials are reused. A new API key or another plugin identity is not required for an upgrade.

Refresh the existing account connection's tool list and start a new conversation if the old one retains cached definitions. Confirm `origin_status.plugin_version` is `0.2.12` and `output_contract.version` is `1.0.0`. Installation and connection verification are separate; verify each signed-in account independently. The known local Work project-sync frontend issue is external and is not repaired by this release.

Read [output contracts](OUTPUT_CONTRACTS.md) for result semantics, malformed-output recovery, media metadata and compatibility. Existing inputs, IDs and scientific field meanings remain unchanged.
