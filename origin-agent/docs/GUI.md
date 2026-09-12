# Origin Companion GUI channel

This channel complements Python, LabTalk, X-Functions and Origin C using the same MCP service, queue and persistent Origin sessions. Prefer native programs for batches. Retrieve control summaries or screenshots only when interaction is needed; users describe goals without learning menu paths or writing code.

## Interface and execution

`origin_gui(session_id, expected_revision, request_id, gui)` supports:

| Action | Behaviour |
| --- | --- |
| `begin` | Save an immutable OPJU checkpoint, return to a writable working project and show managed Origin |
| `observe` | Inspect windows, controls and menus; filter with `query`; optionally capture PNG |
| `invoke` | Use a recently observed menu/button or UIA Invoke, Expand or Legacy default action |
| `set_text` | Set a writable native Edit/UIA Value and read back the full input |
| `select / toggle / expand / collapse` | Use observed UIA patterns and report selection, toggle, expansion and value states |
| `click / drag / scroll` | Use normalised coordinates in the latest screenshot, checking window and pointer-target process |
| `keys / type_text` | Send managed-window shortcuts and Unicode text without using the clipboard |
| `dismiss` | Send Escape to the observed popup and inspect whether it closed |
| `commit` | Once popups close, save OPJU, update the project index and finish the transaction |
| `rollback` | Restore the begin checkpoint, restarting only the session-owned Origin instance if necessary |

Every successful action, including observation, advances the session revision. Duplicate `request_id` values reuse the job. Input is bound to the latest `observation_id` and `target_id`, with PID/creation-time, top-level window, control-state and uniqueness checks. Observations older than 120 seconds or changed contexts reject input.

Do not call Origin COM save/read functions inside modal dialogs. Native programs, standalone batches and project switching are rejected until the transaction ends. Expose only the active popup's targets, even if MFC has not correctly disabled the main window. Inspect the current revision after errors; if input outcome is uncertain, observe instead of automatically replaying it.

## Modules and overhead

- `gui.py`: compact models, stale/duplicate-target validation and summaries.
- `gui_session.py`: transactions, checkpoints, state, screenshot artifacts and recovery.
- `gui_native.py`: Win32 windows/menus/Button/Edit, process identity and single-window captures.
- `gui_accessibility.py`: cached UI Automation observations/actions for Origin MFC menus.
- `gui_input.py`: screenshot/DPI/client coordinates, foreground/pointer checks and Windows SendInput; release keys after interruption.
- `origin_runtime.py`: connection management, including stale originpro 1.1.15 references after process termination.

The added dependency is Windows-only `comtypes==1.4.16` for UI Automation, using OriginExt's MTA threading model. It adds no HTTP or model service. Its compressed wheel was about 289 KiB; actual frozen-package growth must be measured. Summaries contain at most 160 controls, enumeration has time/count budgets, screenshots are opt-in, and full artifacts remain available on demand. These bound context but do not establish billed-token savings.

Adapters handle empty MFC Runtime IDs, zero-area/duplicate accessibility nodes, disappearing dialogs and invalid connections after forced rollback. Legacy default menu actions may leave a menu open; dismiss an observed window and check again. Only observations receive bounded retries, never input replay. Capture failure returns `screenshot_error` without falsely failing a completed save; obtain a valid new image before a visual decision. Sources: [Windows UI Automation](https://learn.microsoft.com/en-us/windows/win32/api/uiautomationclient/nn-uiautomationclient-iuiautomation), [Origin detach](https://docs.originlab.com/originpro/namespaceoriginpro_1_1utils.html).

## Benefits and remaining limits

Native interfaces handle data, analysis and batch plotting; GUI handles required menu/property operations. This reduces menu discovery, repeated form entry and dialog switching. Editable OPJU, checkpoints and read-back support continued review and revision.

Screenshot clicks, drags, scrolls, shortcuts and Unicode input extend access to custom controls without useful UIA patterns. Coordinates are x/y fractions in [0,1) within the latest capture and target `capture.window_id`, not arbitrary desktop coordinates or other applications. Cases cover text selection, dropdowns, Chinese input and saved read-back. Every complex editor, App and dialog still needs task-level acceptance; model, weighting, unit and processing choices need scientific evidence.

Transactions restore the managed Origin project only, not external files, network effects or global settings. They do not take over other unsaved windows. GUI needs an interactive Windows desktop; locked/disconnected remote desktops and other interface languages have not been accepted.

## Reproduce native acceptance

On an activated target build and interactive Windows desktop:

```powershell
uv run python scripts/verify_gui.py --home C:\OriginCompanionTests\gui-new-run
uv run python scripts/verify_gui.py --extended --home C:\OriginCompanionTests\gui-extended-new-run
```

Use empty new directories. Real stdio MCP creates a synthetic workbook, opens Window → Properties, edits Long name, commits and rereads the name and `[1,2,3]`. A second uncommitted edit is rolled back and checked. Stale observations, programs/batches during transactions and commit with an open modal are expected refusals. Screenshots, OPJU, step times and complete results are retained locally, then the test project closes. This script does not substitute for host/model or second-device acceptance.
