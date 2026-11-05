# Origin stdio bridge 0.1.0 candidate

This optional Windows adapter keeps a host's stdio connection open while an idle
Origin frontend exits, then starts the **same original engine** on a later request.
It is a separate candidate, not an Origin upgrade, tunnel repair, installer or
public release. No native Origin runtime is included. Default idle interval: 300 s.

## Scope and compatibility

| Connection | Behavior in this candidate |
|---|---|
| Legacy MCP `initialize` (reviewed SDK 2.2.0) | Idle retirement and automatic wake on the existing outer pipe |
| Modern MCP 2026-07-28 / unknown first method | Conservative passthrough; frontend stays resident |
| Personal OpenAI tunnel / HTTP connection | Unchanged; this adapter does not service that connection |
| Original frozen Origin 0.2.8 and 0.2.15 | Supported only when the complete local package and reviewed source inventory match |
| Arbitrary MCP servers, shell wrappers, changed cores | Refused |

The adapter is host-neutral. Codex/Claude configuration activation and the target
machine's existing 0.2.8 package remain separate acceptance gates. Passing isolated
0.2.15 frontend tests does not establish target-host or native-science acceptance.
Do not claim memory saving for a host that negotiates the modern protocol.

## Safety contract

- Reuse the original absolute executable, arguments, inherited environment, working
  directory, account, state root and profile. Hash-verify the binding and complete
  original runtime at each spawn. A profile or package change requires a new host
  connection. Bindings contain private paths; keep them outside source/distribution.
- Never upgrade the scientific core behind a shared queue. Old frontends can still
  submit old-version plans after migration. Core version equality remains enforced.
- Track both request directions, queued input, uncertain dispatch and unsuccessful
  response delivery. Write complete frames and flush before settling delivery.
  Remap reverse callback IDs per backend generation. Keep bounded queues (64 frames,
  128 MiB per queue) and a 64 MiB frame limit; larger/invalid frames fail closed.
- Only retire after all ledgers are quiet, no persistent job/session is active or
  unknown, the original scheduler/device locks are held, and a quiet ping completes.
  A ping alone is not a quiescence proof. A five-second lease releases locks if
  preparation stalls; no new backend starts until the old owned process exits.
- Close only the stdin pipe owned by this adapter. Never kill, restart or enumerate
  unrelated processes; never close native Origin, cancel scientific jobs, delete
  locks or rewrite queue/session metadata. Failed/unknown execution pins the worker.
- A queued request cancelled before dispatch is removed without executing it.
  Dispatched work is never replayed. A partial write or missing result returns
  `-32010`, `origin_outcome: UNKNOWN`, `retry_safe: false`. Inspect existing work
  before a human decides whether to retry. Proven unsent work uses `-32011`,
  `origin_outcome: NOT_SENT`, `retry_safe: true`. No automatic retry is implemented.
- True host EOF drains known in-flight work and answers callbacks with a closed-host
  error. Cancellation without a terminal response, modern cancelled subscriptions,
  or unknown ownership can retain the adapter/backend indefinitely. This is an
  explicit safety limitation, not a guaranteed bounded shutdown. The external host
  may impose its own process-tree kill policy; this adapter cannot override it.

## Private staging and rollback

Maintenance owns target-machine activation. Keep the old executable/package and
all existing connections intact. Do not use the whole Origin installer or change
the installed-version pointer. Do not restart Codex, Claude, tunnels or native jobs.

1. Extract this standalone package into a new private/versioned directory. Verify
   `checksums.json` and the separately supplied ZIP hash. Keep all `_internal` files.
2. Create a private binding using the exact current server command and arguments:

   ```powershell
   & $bridge bind --backend $originalExe --output $binding -- serve --profile economy
   & $bridge verify --binding $binding
   ```

   The example profile is illustrative: use the current arguments verbatim. Do not
   add, remove or normalize profile/model/vision/environment settings during migration.
3. Copy the complete current host config to a **separate proposed file**. In the
   selected server entry change only `command` to the bridge's absolute path and
   `args` to `["serve", "--binding", "<absolute private binding path>"]`.
   Preserve every other server, environment value, working directory and option.
   JSON uses `mcpServers`; TOML uses `mcp_servers`.
4. Stage and validate the proposal; this writes only a new private receipt directory:

   ```powershell
   & $bridge stage --config $hostConfig --candidate $proposedConfig --binding $binding --bridge $bridge --server $serverName --receipt-dir $receipt
   ```

   The receipt holds exact before/after bytes and hashes. It can contain credentials
   inherited from the original config: use a user-private directory, never Git,
   public artifacts, screenshots or cross-conversation diagnostic messages.
5. Independently verify that this host can load the new config for **future
   connections only**, without replacing any active connections. Confirm no other
   editor/config writer is active. If host hot reload may terminate active work,
   leave the candidate staged until a genuine safe checkpoint. The flag below
   records this human/maintenance judgment; it cannot detect it automatically.

   ```powershell
   & $bridge apply --receipt-dir $receipt --host-checkpoint-confirmed
   ```

   Whole-file hashes are checked immediately before replacement; other edits cause
   refusal. This is not a transaction against uncooperative writers. Windows uses
   [ReplaceFileW](https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-replacefilew)
   with ACL/attribute errors enabled. Existing processes are not controlled by this
   command. Config write success is not proof of host activation.
6. On a new target-host connection, verify initialization, ordinary tool discovery,
   legacy/modern mode, same-pipe idle/wake, no duplicate execution, queued/running
   native work protection, old concurrent development connections and true EOF.
   Measure the owned frontend tree's working set and private bytes; separate the
   adapter, backend and native science process. Record which engine and profile ran.
7. If new-connection acceptance fails, at the same host-safe checkpoint:

   ```powershell
   & $bridge rollback --receipt-dir $receipt --host-checkpoint-confirmed
   ```

   Rollback requires current config to match the exact staged after hash, restores
   original bytes, and refuses to overwrite newer edits. Never force it or stop a
   live adapter with unknown work; leave existing connections to finish naturally.
   Retain both packages until no connection references the adapter.

## Build and evidence

`python scripts/build_stdio_bridge.py --output <new-private-directory>` freezes a
separate stdlib-only executable with PyInstaller, records source hashes before and
after, includes licences and checksums, and verifies the ZIP. It does not install,
publish or include a new Origin core. Run the adapter tests plus the original
portable suite. Independent review, frozen-artifact checks, target host acceptance
and licensed native science are distinct evidence; record pending gates explicitly.

Do not attribute historical tunnel sleep/reboot recovery to this local stdio
candidate. Target-host sleep/reboot/network acceptance must be observed separately
if maintenance changes the connection route.
