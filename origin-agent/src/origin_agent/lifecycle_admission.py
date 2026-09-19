"""Receipt-linked admission fencing for install, recovery and connector entrypoints.

The OS lock bounds concurrent admission; the durable marker survives owner death.
Neither layer grants process ownership or replays a scientific operation.
"""

import os
import threading
import time
import uuid
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path

import psutil

from .storage import BusyError, file_lock, read_json, valid_id, write_json


class AdmissionError(RuntimeError):
    pass


_local = threading.local()


def paths(state_root):
    root = Path(state_root).resolve()
    return root, root / "cloud/.lifecycle-admission.lock", root / "cloud/lifecycle-transaction.json"


def pending_transaction(state_root):
    root, _, marker = paths(state_root)
    if not marker.exists():
        return None
    try:
        value = read_json(marker)
        valid_id(value["receipt_id"])
        valid_id(value["transaction_id"])
        if value["schema_version"] != 1 or Path(value["state_root"]).resolve() != root:
            raise ValueError("invalid scope")
        return value
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise AdmissionError("lifecycle_fence_invalid_recovery_required") from exc


def check_activation_pending(state_root, *, receipt_id=None):
    marker = Path(state_root).resolve() / "cloud/rollback-activation.json"
    if not marker.exists():
        return
    pending = read_json(marker)
    valid_id(pending["receipt_id"])
    if pending["receipt_id"] != receipt_id:
        raise AdmissionError(
            "Private tunnel rollback activation pending; repeat rollback-install " + pending["receipt_id"]
        )


@contextmanager
def _locked(state_root):
    root, lock, _ = paths(state_root)
    with ExitStack() as held:
        try:
            held.enter_context(file_lock(lock, timeout=0))
        except BusyError as exc:
            raise AdmissionError("lifecycle_transaction_busy") from exc
        yield root


@contextmanager
def admitted(state_root):
    """Short, non-reentrant gate. Acquire a runtime scope lock before leaving it."""
    with _locked(state_root) as root:
        pending = pending_transaction(root)
        if pending:
            raise AdmissionError(f"lifecycle_recovery_required:{pending['receipt_id']}")
        yield


@contextmanager
def intent_guard(cloud_root):
    """Serialize short intent read/compare/write steps, never runtime shutdown waits."""
    with ExitStack() as held:
        try:
            held.enter_context(file_lock(Path(cloud_root).resolve() / ".lifecycle-intent.lock", timeout=5))
        except BusyError as exc:
            raise AdmissionError("lifecycle_intent_busy") from exc
        yield


@dataclass
class _Owner:
    receipt_id: str
    transaction_id: str
    resolved: bool = False


def _receipt_status(root, receipt_id):
    receipt = read_json(root / "installations" / receipt_id / "receipt.json")
    if receipt.get("id") != receipt_id:
        raise AdmissionError("lifecycle_receipt_mismatch")
    return receipt.get("status")


def _finish(root, owner, expected):
    if _receipt_status(root, owner.receipt_id) != expected:
        raise AdmissionError("lifecycle_transaction_incomplete")
    owner.resolved = True


@contextmanager
def transaction(state_root, receipt_id, *, recovery=False):
    """Hold admission through all publication and rollback steps.

    Only matching explicit rollback may recover a crashed transaction. Nested rollback
    is permitted solely inside the same thread's owning transaction; ordinary start
    admission never inherits this privilege. Failed rollback retains the fence even if
    the old receipt still says installed.
    """
    valid_id(receipt_id)
    root, _, marker = paths(state_root)
    key = os.path.normcase(str(root))
    owners = getattr(_local, "owners", None)
    if owners is None:
        owners = _local.owners = {}
    existing = owners.get(key)
    if existing is not None:
        if not recovery or existing.receipt_id != receipt_id:
            raise AdmissionError("lifecycle_transaction_busy")
        yield
        _finish(root, existing, "rolled_back")
        return

    with _locked(root):
        # A wrong recovery receipt must not acquire a new durable fence that
        # prevents the outstanding activation's own receipt from recovering.
        check_activation_pending(root, receipt_id=receipt_id if recovery else None)
        pending = pending_transaction(root)
        if pending and (not recovery or pending["receipt_id"] != receipt_id):
            raise AdmissionError(f"lifecycle_recovery_required:{pending['receipt_id']}")
        _receipt_status(root, receipt_id)  # A missing receipt must not create an unrecoverable fence.
        owner = _Owner(receipt_id, uuid.uuid4().hex)
        process = psutil.Process()
        write_json(
            marker,
            {
                "schema_version": 1,
                "state_root": str(root),
                "receipt_id": receipt_id,
                "transaction_id": owner.transaction_id,
                "phase": "rollback" if recovery else "install",
                "observed_at": time.time(),
                "owner": {"pid": process.pid, "created": process.create_time()},
            },
        )
        owners[key] = owner
        try:
            yield
            if not owner.resolved:
                _finish(root, owner, "rolled_back" if recovery else "installed")
        finally:
            owners.pop(key, None)
            if owner.resolved:
                current = pending_transaction(root)
                if not current or current["transaction_id"] != owner.transaction_id:
                    raise AdmissionError("lifecycle_fence_changed_recovery_required")
                marker.unlink()
