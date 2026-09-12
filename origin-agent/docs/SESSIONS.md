# Persistent sessions

A session reuses one managed Origin instance for continued editing. Requests retain the shared SQLite queue, device lock, timeouts and artifact checks; no extra network port or model service is added. Hidden sessions save and exit after a default 180-second idle period, then restore from a checkpoint. `visible=true` sessions remain visible until closed or another task switches the active project.

## Open and continue

Call `origin_session(action="open", request_id="experiment-42", title="Kinetics")`, optionally with `project_path` to load a copy. Wait for its job using `origin_get_job`. The successful `session` result contains `session_id`, `revision` and `checkpoint_id`.

Pass `session_id` and current `expected_revision` with later `origin_run_program` calls. Each success produces a new revision and downloadable OPJU. `RESULTS`, input copies and PNG/PDF/SVG follow the existing contract. Do not recreate the project in every program; open another session to work on a different project.

Repeating the same program at the same session revision returns the same job. Open/checkpoint/restore/close controls use a stable caller `request_id`; changed content with the same ID is rejected. Revision checks happen before mutation, so stale edits do not touch Origin.

`origin_session(action="inspect", session_id=...)` returns the last checkpoint state and bounded project index, with totals and truncation flags; full state stays local. It is not a live GUI observation. Use a program for live numerical read-back and `checkpoint` to capture manual edits/update the index.

## Checkpoints, errors and cancellation

Before mutation, save an immutable recovery file and switch back to mutable `working.opju`. Ordinary Save from code or the user must not overwrite the recovery file. Successful output artifacts also remain immutable; the GUI's active file returns to the working file.

- `checkpoint`: save current state, include managed-window manual changes and increment revision.
- `restore`: provide the current revision and a successful job's `checkpoint_id` from this session; restore and create a new revision. Other sessions' checkpoints are rejected.
- Program error: restore pre-change state without increasing revision; if recovery fails, set `needs_attention`.
- Cancellation/timeout: allow cooperative exit, then terminate only the owned PID with matching creation time if needed. Restore the pre-change checkpoint on the next execution. Cancellation after a verified commit returns success and explicitly reports the commit.
- `close`: save editable OPJU, close the managed instance and mark the session closed.

Recovery covers Origin projects, not general code's external file/network effects. A worker whose supervisor disappears must not commit or overwrite state taken over by a newer worker. Basic GUI transactions and Window Properties modal rollback have been tested; see [GUI.md](GUI.md). Unexpected application closure, complex modals and complete GUI recovery require dedicated cases.

## Modules and evidence

- `sessions.py`: command contract, plan hashes, idempotency, revisions and interrupted recovery.
- `session_worker.py`: supervised worker and atomic file mailbox.
- `session_native.py`: main-thread COM, switching, checkpoints, rollback and visible lifecycle.
- `program_native.py`: shared independent/session execution; live sessions are not reopened after each edit merely for verification.
- `scripts/verify_sessions.py`: continued edits, repeated requests, stale refusals, error rollback, cross-MCP access, cancellation and idle recovery.
- `scripts/verify_session_switching.py`: error after Save, visible-session retention, isolation, wrong-checkpoint rejection and batch coexistence.

Native acceptance uses synthetic data and real MCP calls to the target Origin. It does not certify every host/model, device or function. See [VALIDATION.md](VALIDATION.md).
