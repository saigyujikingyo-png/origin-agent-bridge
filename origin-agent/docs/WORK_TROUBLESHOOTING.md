# Troubleshooting ChatGPT Work

## Confirm the execution computer

In 0.2.8, `origin_status.device.computer_name` identifies the computer running MCP. Compare it with the user's intended device before submitting work; switch connections if it differs. This field does not start Origin, validate licensing or certify a native build. It assists routing, not cryptographic device authentication. Each computer needs its own licensed target Origin, runtime and connection; another computer's success is not this device's acceptance.

## Invalid input appears as a host serialization error

In the 2026-09-12 acceptance run, a session source outside allowed input roots was correctly rejected but appeared as a generic host serialization error. 0.2.7 returned an MCP error with plain text and no structured content. 0.2.8 returns bounded JSON text and structured content for correctable validation, syntax, input and tool errors, retaining the MCP error flag. Full mode, economy and cached full-mode names share this contract; execution is not retried.

Correct the reported input. To continue an output copy, use `origin_run_program` with `project_artifact`. A session accepts `project_path` in configured data roots or the inbox; an internal job path is not automatically an allowed input. The root policy has not changed. Native worker failures remain terminal and need a deliberate corrected submission.

## A project cannot be used for local chat

The message "This project cannot be used for local chat" can occur while ChatGPT prepares a local project mirror, before any plugin call. One Windows client 26.903.9818.0 case on 2026-09-11 logged `stage=filesystem`: an ended task's `node_repl.exe` retained the mirror as its working directory, causing Windows sharing violation 32. After releasing that confirmed idle process, DELETE-access checking passed without changing sync files, permissions or the app database.

This is one diagnosed case, not a universal cause or a plugin fix for the client. If repeated, check whether the associated task is still running; after preserving work, restarting the client may release old helpers. Do not delete `.chatgpt-projects`, alter sync files or bulk-terminate other tasks. An actual client retry is still the end-to-end check.

## Unknown tool

0.2.1 economy mode advertised five tools and routed its 13 full operations through `origin_call`. Old conversations could still send names such as `origin_inspect_dataset` and `origin_plan_workflow`, which that version rejected.

0.2.2 kept five advertised tools while accepting cached full-mode names at dispatch, preserving name/argument/vision/session checks and risk annotations. Each request takes one path; failed execution does not trigger an automatic retry. New conversations should use `origin_help` and `origin_call`; unknown names remain rejected.

Reconnect MCP after an upgrade, and reconnect your existing personal tunnel for cloud Work. If the host rejects a name before sending it, refresh its tool list or start a new Work conversation. Do not change models or create a new model key solely for this error. Confirm inspection/planning with synthetic data before authorised real work. Startup/protocol checks are not host-model acceptance.

## Cloud metadata versus an existing conversation

In a real 2026-09-11 case, the backend returned 0.2.2 while the cloud app still registered eight early tools. Reconnecting the tunnel alone did not refresh metadata. The observed web flow was Settings → Plugins → Origin app → Refresh, then confirm five economy tools including `origin_help`, `origin_call` and `origin_recipe`. Older installations may display Origin Agent Bridge; rename the same app rather than recreating it or its key. UI wording/location can change.

The existing task retained its old eight-tool registry even after refresh and another mention. Compatibility dispatch let it import, fit, reopen OPJU and export figures, but could not expose names the host had never registered. A new authorised task successfully used `origin_status`, `origin_help` and `origin_call` for `origin_capabilities`, discovering five tools and 13 operations including programs, sessions and GUI. That was read-only discovery, not execution of every capability.

OpenAI's [Developer mode and MCP apps](https://help.openai.com/en/articles/12584461) distinguishes server changes from registered metadata. Specific UI/cache behaviour here is observed evidence. See [cloud-work-0.2.2.json](../verification/cloud-work-0.2.2.json). One interrupted PDF-info read succeeded on a read-only retry; uncertain writes must first be checked by job ID.

In the 0.2.8 refresh, actual Work reported one successful status call returning 0.2.8, while the old alias in a long development conversation still returned `Unknown tool`. These are separate observations; see the [refresh receipt](../verification/local-refresh-0.2.8.json).

## Cloud goes offline after Codex exits

A later 2026-09-11 test returned `Tunnel-client has not been seen for 300 seconds`: local MCP worked, but the old tunnel process had exited. A new login task also exposed an MSIX issue: configuration seen by Codex under `AppData/Roaming/tunnel-client/origin-agent.yaml` actually lived under its package `LocalCache/Roaming`, invisible to the ordinary scheduled task.

Connection/startup scripts now use `.origin-agent/cloud/profiles`, retaining the user's identity. A current-user background task reads `.origin-agent/install.json` and manages the connection independently. See [INSTALL.md](INSTALL.md). Record outage, recovered status, native success and process independence separately; one ready status does not prove continuous availability.

A 0.2.3 injected exit did not recover despite scheduler retry settings after re-registering a running task; the Windows cause remained unknown. From 0.2.4 the resident supervisor directly monitors the connection process and creation time, retries after 5/15/30 seconds up to three times, and resets after five stable minutes. The scheduled task still handles login startup. Stop/disable that task before deliberately stopping its tunnel so intentional disconnection is not treated as a fault. This mechanism does not guarantee every cloud request succeeds.

## Long wait after a job has already failed

A deleted trial left local NumPy-import and nonexistent `GLayer.set_label` failures, with no verified figure or OPJU. Without the original conversation, its entire waiting time and cloud retrieval delay cannot be reconstructed.

0.2.6 reports failed/cancelled/interrupted jobs as `terminal=true`, with no later-poll instruction, the last stage and recovery guidance. Report failure promptly; correct it before submitting again. Continued polling is not recovery.

After retrieving cloud data, use `origin_import_table` for CSV/TSV and `origin_recipe(recipe="beer_lambert")` for standard calibration. This reuses native fitting, independent numbers, OPJU reopen and export checks. Supply intercept/weighting explicitly; absorptivity also needs actual path length and concentration units. General Python is available, but standard fits should not require temporary code or undeclared packages.

If no tools are available, check the installed-plugin list, not only the personally created directory. One 2026-09-11 case still showed Install for an existing personal Origin Companion app. Restoring it required an actual call to verify connectivity. Keep connection, model selection and scientific execution failures distinct.

## Files exist locally but Work has no attachments

`info` and `origin://` references establish local existence, not cloud receipt. `origin_get_artifact(mode="download")` returns an embedded binary MCP resource; verify its full size and SHA-256. Info mode does not transfer binary. Files over 32 MiB are explicitly refused, never truncated.

If the host does not create attachments, request `origin_help(operation="origin_get_artifact", query="receiver")`. The fixed receiver writes a new temporary file in the host output directory, streams chunks, verifies completeness and only then exposes the artifact without overwriting earlier results. It adds no public service or manual user decoding. See [file delivery](../skills/origin-workflow/references/FILE_DELIVERY.md).

Earlier temporary receivers failed by assuming `atob` existed or using non-TTY stdin that immediately returned EOF. Those are transfer-method errors, not evidence that Origin stalled or the host cannot write files. The fixed receiver avoids both. If a host truly cannot save/execute files, state that limit; do not invent URLs or label local paths as cloud attachments.

0.2.7 also converts numeric Unicode superscripts/subscripts to Origin text formatting while preserving original inputs/requests. Reopen checks verify saved formatting; visual review still matters for fonts/layout.

## Downloads and university OneDrive

Use the user's chosen local folder, host attachment or other authorised destination. University OneDrive is a development archive preference, not a runtime/delivery requirement. The user confirmed successful downloading to their own Downloads folder. A historical `ERR_BLOCKED_BY_CLIENT` route remains recorded with its exact blocking component unknown; it does not establish failure at every destination. A user-reported download does not by itself supply per-file hash evidence for all artifacts. See [0.2.8 acceptance](../../WORK_ACCEPTANCE_0.2.8.md).
