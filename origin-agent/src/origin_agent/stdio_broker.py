"""Opt-in stdlib stdio adapter for a fingerprint-bound, unchanged Origin engine.

Never retry a forwarded request. A backend can retire only after its complete
request ledger and delivery are empty, execution fences are held, and a quiet
ping barrier has completed. This is not a generic MCP subprocess supervisor.
"""

import argparse
import collections
import json
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from .stdio_idle import IdleControl

BRIDGE_VERSION = "0.1.0"
MAX_FRAME = 64 * 1024 * 1024


def message_key(identifier):
    if isinstance(identifier, bool) or not isinstance(identifier, (str, int)):
        raise ValueError("Invalid request ID")
    if isinstance(identifier, str) and len(identifier) > 1024:
        raise ValueError("Request ID too large")
    # The pinned SDK coerces numeric string IDs into its integer correlation domain.
    try:
        return "number", int(identifier)
    except ValueError:
        return "string", identifier


def validate_message(value):
    """Only a valid terminal MCP envelope can settle an execution ledger entry."""
    if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
        raise ValueError("Invalid JSON-RPC message")
    if "method" in value:
        if not isinstance(value["method"], str) or not value["method"]:
            raise ValueError("Invalid method")
        if "result" in value or "error" in value:
            raise ValueError("Ambiguous request envelope")
        if value.get("params") is None:
            # The pinned SDK treats explicit null like omitted optional params.
            value["params"] = {}
        if not isinstance(value["params"], dict):
            raise ValueError("Invalid MCP params")
        if "id" in value:
            message_key(value["id"])
        return
    if "id" not in value or "params" in value or ("result" in value) == ("error" in value):
        raise ValueError("Invalid response envelope")
    if "result" in value:
        message_key(value["id"])
        if not isinstance(value["result"], dict):
            raise ValueError("Invalid MCP result")
    else:
        error = value["error"]
        if (
            not isinstance(error, dict)
            or type(error.get("code")) is not int
            or not isinstance(error.get("message"), str)
        ):
            raise ValueError("Invalid JSON-RPC error")
        if value["id"] is not None:
            message_key(value["id"])


class Events:
    """Bound reader threads by both bytes and message count; backpressure stays on pipes."""

    def __init__(self):
        self.condition = threading.Condition()
        self.items = collections.deque()
        self.size = 0
        self.closed = False

    def put(self, source, generation, raw):
        size = len(raw) if isinstance(raw, bytes) else 0
        with self.condition:
            while not self.closed and (self.size + size > MAX_FRAME * 2 or len(self.items) >= 64):
                self.condition.wait()
            if self.closed:
                return
            self.items.append((source, generation, raw, size))
            self.size += size
            self.condition.notify_all()

    def get(self, timeout):
        with self.condition:
            if not self.items:
                self.condition.wait(timeout)
            if not self.items:
                raise queue.Empty
            source, generation, raw, size = self.items.popleft()
            self.size -= size
            self.condition.notify_all()
            return source, generation, raw

    def empty(self):
        with self.condition:
            return not self.items

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify_all()


class Broker:
    def __init__(
        self,
        command,
        root,
        expected_version,
        *,
        stdin=None,
        stdout=None,
        env=None,
        idle_seconds=300.0,
        verify=None,
        diagnostic=None,
        cwd=None,
        clock=time.monotonic,
    ):
        self.command = list(command)
        self.root = Path(root).resolve()
        self.expected_version = expected_version
        self.stdin = stdin or sys.stdin.buffer
        self.stdout = stdout or sys.stdout.buffer
        self.env = env
        self.cwd = str(cwd or Path.cwd())
        self.idle_seconds = idle_seconds
        self.verify = verify or (lambda: None)
        self.diagnostic = diagnostic
        self.clock = clock
        self.events = Events()
        self.nonce = uuid.uuid4().hex
        self.prefix = "origin-bridge-" + self.nonce + "-"
        self.sequence = 0
        self.generation = 0
        self.process = None
        self.phase = "cold"
        self.pending = {}
        self.admitted = set()
        self.uncertain_inflight = set()
        self.uncertain_owner = False
        self.undelivered = set()
        self.reverse = {}
        self.internal = None
        self.waiting = collections.deque()
        self.waiting_bytes = 0
        self.initialize_params = None
        self.initialize_result = None
        self.protocol_mode = None
        self.initialized = False
        self.input_closed = False
        self.eof_handled = False
        self.output_closed = False
        self.pins = set()
        self.last_activity = clock()
        self.next_idle_check = self.last_activity
        self.guard = IdleControl(self.root, self.nonce)
        self.lease = None
        self.backend_eof = False
        self.exit_status = 0
        self.last_record = None

    def _record(self):
        if self.diagnostic:
            from .storage import write_json

            record = {
                "bridge_version": BRIDGE_VERSION,
                "phase": self.phase,
                "protocol_mode": self.protocol_mode,
                "backend_generation": self.generation,
                "backend_alive": self.process is not None,
                "inflight": len(self.pending),
                "reverse_requests": len(self.reverse),
                "uncertain_inflight": len(self.uncertain_inflight),
                "undelivered": len(self.undelivered),
                "uncertain_owner": self.uncertain_owner,
                "retained_reasons": sorted(self.pins),
                "input_closed": self.input_closed,
            }
            if record != self.last_record:
                try:
                    write_json(Path(self.diagnostic), record)
                except OSError:
                    # Optional diagnostics must never interrupt protocol or backend ownership.
                    self.diagnostic = None
                self.last_record = record

    def _id(self):
        self.sequence += 1
        return self.prefix + str(self.sequence)

    def _read(self, stream, source, generation):
        try:
            while True:
                raw = stream.readline(MAX_FRAME + 1)
                if not raw:
                    break
                if len(raw) > MAX_FRAME or not raw.endswith(b"\n"):
                    self.events.put(source, generation, "invalid_frame")
                    return
                self.events.put(source, generation, raw)
                raw = None
        except (OSError, ValueError):
            self.events.put(source, generation, "read_error")
        finally:
            self.events.put(source, generation, None)

    def _wire(self, stream, value, raw=None):
        data = raw or (json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode() + b"\n")
        remaining = memoryview(data)
        while remaining:
            written = stream.write(remaining)
            if not isinstance(written, int) or written <= 0 or written > len(remaining):
                raise OSError("Pipe write did not confirm delivery")
            remaining = remaining[written:]
        stream.flush()

    def _emit(self, value, raw=None):
        if self.output_closed:
            return False
        try:
            self._wire(self.stdout, value, raw)
            return True
        except (BrokenPipeError, OSError, ValueError):
            self.output_closed = self.input_closed = True
            self._pin("output_delivery_failed")
            return False

    def _error(self, identifier, outcome, message):
        delivered = self._emit(
            {
                "jsonrpc": "2.0",
                "id": identifier,
                "error": {
                    "code": -32010 if outcome == "UNKNOWN" else -32011,
                    "message": message,
                    "data": {"origin_outcome": outcome, "retry_safe": outcome == "NOT_SENT"},
                },
            }
        )
        if identifier is not None:
            key = message_key(identifier)
            self.admitted.discard(key)
            if not delivered:
                self.undelivered.add(key)

    def _pin(self, reason):
        self.pins.add(reason)
        self.guard.mark_uncertain()

    def _release_lease(self):
        if self.lease:
            self.guard.handle({"token": self.nonce, "action": "abort", "lease": self.lease})
        self.lease = None

    def _start(self):
        assert self.process is None
        self.verify()
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            env=self.env,
            cwd=self.cwd,
            bufsize=0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.generation += 1
        self.backend_eof = False
        self.phase = "starting" if self.initialize_result is None else "waking"
        threading.Thread(
            target=self._read,
            args=(self.process.stdout, "backend", self.generation),
            daemon=True,
        ).start()
        if self.initialize_result is not None:
            self._internal_request("wake", "initialize", self.initialize_params)
        self._record()

    def _internal_request(self, kind, method, params):
        identifier = self._id()
        self.internal = {"id": identifier, "kind": kind, "deadline": self.clock() + 10}
        try:
            self._wire(
                self.process.stdin,
                {
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "method": method,
                    "params": params,
                },
            )
        except (OSError, ValueError):
            self._pin("backend_write_uncertain")
            self.uncertain_owner = True
            self.phase = "unconfirmed"
            self._release_lease()

    def _enqueue(self, value, raw):
        if self.phase == "unconfirmed" and "id" in value and "method" in value:
            self._error(value["id"], "NOT_SENT", "Backend state is unconfirmed; request was not sent.")
            return
        if len(self.waiting) >= 64 or self.waiting_bytes + len(raw) > MAX_FRAME * 2:
            if "id" in value and "method" in value:
                self._error(value["id"], "NOT_SENT", "Pending input limit reached; request was not sent.")
            else:
                self._pin("unhandled_notification")
            return
        self.waiting.append((value, raw))
        self.waiting_bytes += len(raw)

    def _forward(self, value, raw=None):
        identifier = value.get("id")
        key = None
        if "id" in value and "method" in value:
            key = message_key(identifier)
            if key in self.pending or (isinstance(identifier, str) and identifier.startswith(self.prefix)):
                self._error(identifier, "NOT_SENT", "Request ID is already in use or reserved.")
                return
            # Register BEFORE write: a failed/partial pipe write is an unknown outcome.
            self.pending[key] = {"id": identifier, "method": value["method"]}
        try:
            self._wire(self.process.stdin, value, raw)
        except (OSError, ValueError):
            self._pin("backend_write_uncertain")
            self.phase = "unconfirmed"
            if key is not None:
                self.pending.pop(key, None)
                self.uncertain_inflight.add(key)
                self._error(
                    identifier, "UNKNOWN", "Backend write failed; inspect existing work before retrying."
                )
            else:
                self.uncertain_owner = True

    def _drain_waiting(self):
        while self.waiting and self.phase in {"active", "starting"}:
            value, raw = self.waiting.popleft()
            self.waiting_bytes -= len(raw)
            self._forward(value, raw)

    def _reject_waiting(self, message):
        while self.waiting:
            value, raw = self.waiting.popleft()
            self.waiting_bytes -= len(raw)
            if "id" in value and "method" in value:
                self._error(value["id"], "NOT_SENT", message)
            else:
                self._pin("unhandled_notification")

    def _host(self, value, raw):
        if value.get("id", False) is None:
            self._pin("uncorrelated_client_error")
            return
        if "method" not in value:
            self.last_activity = self.clock()
            key = message_key(value.get("id"))
            callback = self.reverse.pop(key, None)
            if callback and callback["generation"] == self.generation and self.process is not None:
                value["id"] = callback["original_id"]
                self._forward(value)
            else:
                self._pin("unmatched_client_response")
            return
        method = value["method"]
        if "id" in value:
            key = message_key(value["id"])
            if (
                key in self.admitted
                or key in self.uncertain_inflight
                or (isinstance(value["id"], str) and value["id"].startswith(self.prefix))
            ):
                self._pin("duplicate_request_id")
                self._emit(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32600,
                            "message": "Request ID is already in use or reserved.",
                        },
                    }
                )
                return
            self.admitted.add(key)
        if self.protocol_mode is None:
            self.protocol_mode = "legacy" if method == "initialize" else "passthrough"
            if self.protocol_mode == "passthrough":
                self._pin("modern_or_unknown_protocol_passthrough")
        if method == "ping" and "id" in value and self.protocol_mode == "legacy":
            if not self._emit({"jsonrpc": "2.0", "id": value["id"], "result": {}}):
                self.undelivered.add(message_key(value["id"]))
            self.admitted.discard(message_key(value["id"]))
            # Transport keepalives must not retain an otherwise idle scientific frontend.
            return
        self.last_activity = self.clock()
        if method == "initialize" and self.protocol_mode == "legacy":
            if self.initialize_params is not None or len(raw) > 256 * 1024:
                self._error(value.get("id"), "NOT_SENT", "Initialization requires a new connection.")
                return
            self.initialize_params = value.get("params", {})
        elif self.initialize_params is None and self.protocol_mode == "legacy":
            if "id" in value:
                self._error(value["id"], "NOT_SENT", "Initialize the connection first.")
            return
        if method == "notifications/initialized":
            self.initialized = True
        elif method == "notifications/cancelled":
            self._pin("cancellation_observed")
            cancelled = message_key(value.get("params", {}).get("requestId"))
            for index, (queued, queued_raw) in enumerate(self.waiting):
                if "id" in queued and "method" in queued and message_key(queued["id"]) == cancelled:
                    if queued["method"] not in {"initialize", "server/discover"}:
                        # Proven unsent work can be cancelled without ever dispatching it.
                        del self.waiting[index]
                        self.waiting_bytes -= len(queued_raw)
                        self.admitted.discard(cancelled)
                        return
        elif method.startswith("notifications/"):
            self._pin("untracked_notification_state")
        elif method in {"resources/subscribe", "resources/unsubscribe"}:
            self._pin("subscription_state")
        if self.phase == "preparing":
            self._release_lease()
            # Finish the harmless barrier once; new requests stay unsent until its response.
        self._enqueue(value, raw)
        if self.process is None:
            try:
                self._start()
            except Exception:
                self._reject_waiting("Bound backend is unavailable or changed; no request was sent.")
                self.phase = "cold"
        self._drain_waiting()

    def _initialization_matches(self, result):
        if not isinstance(result, dict) or not isinstance(result.get("serverInfo"), dict):
            return False
        if result["serverInfo"].get("version") != self.expected_version:
            return False
        capabilities = result.get("capabilities", {})
        if not isinstance(capabilities, dict) or not isinstance(capabilities.get("resources", {}), dict):
            return False
        if capabilities.get("resources", {}).get("subscribe") or capabilities.get("experimental"):
            self._pin("unsupported_background_capability")
        return self.initialize_result is None or all(
            result.get(key) == self.initialize_result.get(key)
            for key in ("protocolVersion", "capabilities", "serverInfo", "instructions")
        )

    def _internal_response(self, value):
        control, self.internal = self.internal, None
        if control["kind"] == "wake":
            if "error" in value or not self._initialization_matches(value.get("result")):
                self._pin("wake_identity_unconfirmed")
                self.phase = "unconfirmed"
                self._reject_waiting("Backend identity changed during wake; requests were not sent.")
                return
            if self.initialized:
                self._forward({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
                if self.phase == "unconfirmed":
                    self._reject_waiting(
                        "Backend initialization delivery is unconfirmed; requests were not sent."
                    )
                    return
            self.phase = "active"
            self._drain_waiting()
            return
        if value.get("result") != {} or "error" in value:
            self._pin("idle_barrier_unconfirmed")
        committed = False
        if self.lease and not self.pins and not self.waiting and not self.reverse and self.events.empty():
            answer = self.guard.handle({"token": self.nonce, "action": "commit", "lease": self.lease})
            if answer.get("allowed"):
                try:
                    committed = self.guard.retire(self.process.stdin.close)
                except (OSError, ValueError):
                    self._pin("retirement_unconfirmed")
        if committed:
            self.phase = "retiring"
        else:
            self._release_lease()
            self.phase = "active"
            self.next_idle_check = self.clock() + min(15, self.idle_seconds)
            self._drain_waiting()

    def _backend(self, value, raw):
        self.last_activity = self.clock()
        if value.get("id", False) is None:
            self._pin("uncorrelated_backend_error")
            self._emit(value, raw)
            return
        if "method" in value:
            if "id" in value:
                original = value["id"]
                if self.input_closed:
                    self._forward(
                        {
                            "jsonrpc": "2.0",
                            "id": original,
                            "error": {
                                "code": -32000,
                                "message": "Host input closed.",
                            },
                        }
                    )
                    return
                external = self._id()
                self.reverse[message_key(external)] = {"original_id": original, "generation": self.generation}
                value["id"] = external
                self._emit(value)
            else:
                if value["method"] == "notifications/cancelled":
                    self._pin("cancellation_observed")
                    original = value.get("params", {}).get("requestId")
                    for key, callback in self.reverse.items():
                        if (
                            self.protocol_mode == "legacy"
                            and callback["generation"] == self.generation
                            and (message_key(callback["original_id"]) == message_key(original))
                        ):
                            value["params"]["requestId"] = key[1]
                            raw = None
                            break
                elif not self.pending or value["method"] != "notifications/progress":
                    self._pin("untracked_backend_notification")
                self._emit(value, raw)
            if self.phase == "preparing":
                self._release_lease()
            return
        if self.internal and value.get("id") == self.internal["id"]:
            self._internal_response(value)
            return
        key = message_key(value.get("id"))
        if key in self.uncertain_inflight:
            # UNKNOWN was already returned exactly once. Completion only resolves retention.
            self.uncertain_inflight.discard(key)
            return
        request = self.pending.get(key)
        if request is None:
            self._pin("unmatched_backend_response")
            return
        result = value.get("result")
        if request["method"] == "initialize" and self.protocol_mode == "legacy":
            if not self._initialization_matches(result):
                self._pin("backend_identity_unconfirmed")
                self.pending.pop(key)
                self._error(
                    request["id"], "UNKNOWN", "Backend initialization identity is not the bound version."
                )
                self.phase = "unconfirmed"
                return
            self.initialize_result = result
            self.phase = "active"
        if "error" in value or (isinstance(result, dict) and result.get("isError")):
            self._pin("failed_or_unknown_result")
        if isinstance(result, dict) and result.get("resultType", "complete") != "complete":
            self._pin("continuation_or_extension_state")
        if self.protocol_mode == "passthrough" and self.phase == "starting":
            self.phase = "active"
        if value["id"] != request["id"] or type(value["id"]) is not type(request["id"]):
            value["id"] = request["id"]
            raw = None
        if not self._emit(value, raw):
            self.undelivered.add(key)
        # Removal is after stdout.flush; blocked/partial delivery cannot qualify as idle.
        self.pending.pop(key, None)
        self.admitted.discard(key)

    def _backend_closed(self):
        self.backend_eof = True
        if self.pending or self.reverse or self.uncertain_inflight:
            self.uncertain_owner = True
        for request in list(self.pending.values()):
            self._pin("backend_exit_with_request")
            self.uncertain_inflight.add(message_key(request["id"]))
            self._error(
                request["id"], "UNKNOWN", "Backend exited after dispatch; inspect work before retrying."
            )
        self.pending.clear()
        if self.reverse:
            self._pin("backend_exit_with_callback")
            self.reverse.clear()
        if self.internal and self.internal["kind"] == "wake":
            self._reject_waiting("Backend exited during initialization; requests were not sent.")
        self.internal = None
        self._release_lease()

    def _eof(self):
        self.input_closed = True
        self.eof_handled = True
        self._release_lease()
        for key, callback in list(self.reverse.items()):
            if self.process is not None:
                self._forward(
                    {
                        "jsonrpc": "2.0",
                        "id": callback["original_id"],
                        "error": {
                            "code": -32000,
                            "message": "Host input closed.",
                        },
                    }
                )
            self.reverse.pop(key, None)

    def _tick(self):
        if self.process is not None and self.backend_eof and self.process.poll() is not None:
            self.process.stdout.close()
            if not self.process.stdin.closed:
                self.process.stdin.close()
            self.process = None
            self.uncertain_inflight.clear()
            self.uncertain_owner = False
            self.phase = "cold"
            if self.waiting and not self.input_closed:
                try:
                    self._start()
                except Exception:
                    self._reject_waiting("Bound backend is unavailable; requests were not sent.")
        if self.internal and self.clock() >= self.internal["deadline"]:
            # No force-kill or second owner on a timeout. A late response may still resolve it.
            self._pin("protocol_deadline_unconfirmed")
            self._release_lease()
            self.phase = "unconfirmed"
            self._reject_waiting("Backend response is unconfirmed; requests were not sent.")
        if self.input_closed:
            if not self.eof_handled:
                self._eof()
            self._reject_waiting("Host closed before dispatch; request was not sent.")
            if (
                self.process is not None
                and not self.pending
                and not self.reverse
                and not self.internal
                and not self.uncertain_inflight
                and not self.uncertain_owner
            ):
                if not self.process.stdin.closed:
                    self.process.stdin.close()
                self.phase = "closing"
            return
        now = self.clock()
        if (
            self.phase == "active"
            and self.protocol_mode == "legacy"
            and self.initialized
            and self.initialize_result is not None
            and not self.pending
            and not self.reverse
            and not self.waiting
            and not self.internal
            and not self.pins
            and not self.uncertain_inflight
            and not self.undelivered
            and self.events.empty()
            and now >= self.next_idle_check
            and now - self.last_activity >= self.idle_seconds
        ):
            answer = self.guard.handle({"token": self.nonce, "action": "prepare"})
            self.next_idle_check = now + min(15, self.idle_seconds)
            if answer.get("allowed"):
                self.lease = answer["lease"]
                self.phase = "preparing"
                self._internal_request("idle", "ping", {})

    def run(self):
        threading.Thread(target=self._read, args=(self.stdin, "host", 0), daemon=True).start()
        self._record()
        try:
            while not (self.input_closed and self.process is None):
                try:
                    source, generation, raw = self.events.get(0.05)
                except queue.Empty:
                    self._tick()
                    self._record()
                    continue
                if source == "backend" and generation != self.generation:
                    continue
                if raw is None:
                    self._eof() if source == "host" else self._backend_closed()
                elif not isinstance(raw, bytes):
                    self._pin("protocol_frame_unconfirmed")
                    if source == "host":
                        self._eof()
                    self.exit_status = 1
                else:
                    try:
                        value = json.loads(raw)
                        validate_message(value)
                        (self._host if source == "host" else self._backend)(value, raw)
                    except (ValueError, TypeError, KeyError):
                        self._pin("protocol_message_unconfirmed")
                        self.exit_status = 1
                        if source == "host":
                            self._emit(
                                {
                                    "jsonrpc": "2.0",
                                    "id": None,
                                    "error": {
                                        "code": -32600,
                                        "message": "Invalid or unsupported protocol message.",
                                    },
                                }
                            )
                    value = None
                raw = None
                self._tick()
                self._record()
        finally:
            self.guard.close()
            self.events.close()
        return self.exit_status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="Origin stdio bridge " + BRIDGE_VERSION)
    actions = parser.add_subparsers(dest="action", required=True)
    bind = actions.add_parser("bind", help="Create a private binding; do not change host configuration")
    bind.add_argument("--backend", type=Path, required=True)
    bind.add_argument("--output", type=Path, required=True)
    bind.add_argument("backend_args", nargs=argparse.REMAINDER)
    serve = actions.add_parser("serve", help="Preserve host stdio and lazily run the bound original engine")
    serve.add_argument("--binding", type=Path, required=True)
    serve.add_argument("--idle-seconds", type=float, default=300)
    serve.add_argument("--diagnostic", type=Path)
    verify = actions.add_parser("verify", help="Read-only validation of the private binding")
    verify.add_argument("--binding", type=Path, required=True)
    stage = actions.add_parser(
        "stage", help="Validate a proposed host config and create private backups; never activate"
    )
    stage.add_argument("--config", type=Path, required=True)
    stage.add_argument("--candidate", type=Path, required=True)
    stage.add_argument("--binding", type=Path, required=True)
    stage.add_argument("--bridge", type=Path, required=True)
    stage.add_argument("--server", required=True)
    stage.add_argument("--receipt-dir", type=Path, required=True)
    for action in ("apply", "rollback"):
        migration = actions.add_parser(action, help="Maintenance only, at a verified host-safe checkpoint")
        migration.add_argument("--receipt-dir", type=Path, required=True)
        migration.add_argument("--host-checkpoint-confirmed", action="store_true")
    args = parser.parse_args()
    from .stdio_binding import create_binding, load_binding

    try:
        if args.action in {"stage", "apply", "rollback"}:
            from .stdio_migration import replace_configuration, stage_configuration

            if args.action == "stage":
                receipt = stage_configuration(
                    args.config, args.candidate, args.binding, args.bridge, args.server, args.receipt_dir
                )
                print(
                    json.dumps(
                        {
                            "staged": True,
                            "before_sha256": receipt["before_sha256"],
                            "after_sha256": receipt["after_sha256"],
                        }
                    )
                )
            else:
                replace_configuration(
                    args.receipt_dir,
                    rollback=args.action == "rollback",
                    checkpoint=args.host_checkpoint_confirmed,
                )
                print(json.dumps({"configuration": args.action, "runtime_activation": "not_observed"}))
            return 0
        if args.action == "bind":
            backend_args = args.backend_args or ["serve"]
            if backend_args[0] == "--":
                backend_args = backend_args[1:]
            print(json.dumps(create_binding(args.backend, backend_args, args.output)))
            return 0
        binding = load_binding(args.binding)
        if args.action == "verify":
            binding.verify()
            print(json.dumps({"valid": True, "engine_version": binding.version}))
            return 0
        if not 0.1 <= args.idle_seconds <= 3600:
            parser.error("idle-seconds must be between 0.1 and 3600; production default is 300")
        return Broker(
            binding.command,
            binding.root,
            binding.version,
            idle_seconds=args.idle_seconds,
            verify=binding.verify,
            cwd=binding.cwd,
            env=binding.environment,
            diagnostic=args.diagnostic,
        ).run()
    except (OSError, ValueError, KeyError, TypeError):
        print("Origin stdio bridge: backend binding could not be verified.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
