# One Origin Companion across OpenAI surfaces

## The user-facing entry

Use **one registered Origin Companion plugin** in your OpenAI account for Chat, cloud Work, local Work and Codex. Install the Windows execution core once on the computer with your activated Origin. That same private connection routes every request to the same core; it does not move Origin into the cloud.

The previous local marketplace plugin and developer-mode cloud app were separate registrations. Giving both the same display name did not merge them. Since 0.2.9, the recommended OpenAI setup keeps the registered app and retires the duplicate local marketplace entry. Claude, WorkBuddy and generic MCP hosts continue to use the same execution core through their local adapters. ZIP and MCPB are packaging formats of one version, not separate products.

## Existing users

1. Keep your existing Origin computer and private tunnel running. Reuse your account, tunnel profile and encrypted key.
2. Install the current Windows ZIP. Double-click **Connect-OpenAI.cmd**.
3. Open **My plugins**, connect your existing Origin Companion if necessary, and copy its details-page link into the setup window. Do not create another Origin plugin or API key.
4. Leave **Retire the older local Origin Companion plugin entry** selected, then save. The setup checks the registered app through the installed Codex protocol without starting a model call. It requires the expected enabled Origin tool names before retiring an old entry.
5. Start a new Chat, Work or Codex task and select the same Origin Companion. Ask for its status before real work. Old conversations may retain outdated tool names or local servers.

The setup window remains responsive while the bounded connection check runs. It saves only the registered app identifier and canonical plugin URL in `%USERPROFILE%\.origin-agent\openai-connection.json`. This is account-local configuration, never a public manifest or shared release asset. New users still need the account/tunnel setup in [INSTALL.md](INSTALL.md); this window does not create a cloud account, tunnel or API key.

## What consolidation changes

- Removes only the known `origin-agent@personal` local entry, using the official Codex uninstall command, followed by a targeted catalog migration.
- Removes a legacy direct `origin-agent` Codex MCP entry only when its executable and arguments identify an installation owned by this runtime. Unexpected entries are preserved for review.
- Preserves other personal plugins, global agent settings, Claude/WorkBuddy adapters, the local plugin source folder, private connection credentials, data, jobs and sessions.
- Backs up modified files and refuses to overwrite concurrent edits. If the old cache is in use, configuration is restored and consolidation reports failure; close old Origin Companion tasks and retry.
- Publishes the same English name, description and blue open-circle icon in portable metadata and MCP initialization. A host may cache or ignore MCP icon metadata; this does not create a second connection.

To restore configuration, use the installation receipt with `origin-agent rollback-install RECEIPT_ID`. If the old local plugin cache was removed, reinstall `origin-agent@personal` with the official Codex plugin command after restoring its catalog entry. This restores the old two-registration setup; it is a rollback path, not the recommended everyday setup.

## Availability and limitations

OpenAI's [plugin guide](https://learn.chatgpt.com/docs/plugins) describes support across Chat, Work and Codex, with account, workspace and desktop-only restrictions. Its [packaging guide](https://developers.openai.com/plugins/build/plugins) distinguishes local bundles from registered app mappings. A local Windows stdio command alone cannot run in cloud Chat or Work. Publishing a private account's registered ID in a GitHub plugin would not give classmates their own Origin installation.

The unified OpenAI route requires internet access and the user's private connection, even when the agent runs locally. The Origin computer must be on, licensed and reachable. GUI operations additionally need an interactive desktop. For offline local MCP use, an advanced `codex-direct` adapter remains available; enabling it alongside the registered app intentionally adds a second route and is outside the single-entry setup.

Status/help tests establish connection availability, not every Origin operation or file-delivery behavior. See [0.2.9 acceptance](https://github.com/saigyujikingyo-png/origin-agent-bridge/blob/codex/origin-companion-release/WORK_ACCEPTANCE_0.2.9.md) for the exact tested surfaces and remaining gaps. The scientific core and five-tool economy interface are shared; capability and licence limits remain unchanged.

## If local Work cannot apply a project

The desktop message **"Could not use this project for a local chat"** can occur before the plugin is called. In the investigated case, an existing Work session held the project cache directory open, and Windows refused the application's directory replacement during project synchronisation.

A projectless task can help isolate the issue, but it did not resolve the reported case: the desktop still attempted project synchronisation. Finish existing project tasks, fully exit and restart the desktop app, then try a new local Work task and request `origin_status`. This recovery has not yet been verified for the affected session. Do not delete project files or recreate the Origin connection to address this message. The plugin cannot patch the host application's synchronisation behavior.
