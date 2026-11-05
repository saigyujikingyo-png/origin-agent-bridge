import io
import json
import os
import queue
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from origin_agent.stdio_broker import Broker, message_key, validate_message
from origin_agent.stdio_idle import IdleControl
from origin_agent.storage import file_lock, read_json, write_json


class Host:
    def __init__(self, root, *, idle=0.2):
        self.root = root
        self.output = queue.Queue()
        self.saved = []
        self.counter = 100
        self.errors = (root / "fixture-stderr.log").open("wb")
        self.process = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name("stdio_fixture_adapter.py"))],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.errors,
            env={**os.environ, "ORIGIN_AGENT_HOME": str(root), "FIXTURE_IDLE": str(idle)},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        def reader():
            for line in self.process.stdout:
                self.output.put(json.loads(line))

        self.reader = threading.Thread(target=reader, daemon=True)
        self.reader.start()

    def send(self, value):
        self.process.stdin.write(json.dumps(value).encode() + b"\n")
        self.process.stdin.flush()

    def receive(self, identifier=None, *, method=None, timeout=8):
        deadline = time.monotonic() + timeout

        def matches(value):
            return (
                value.get("method") == method
                if method
                else value.get("id") == identifier and "method" not in value
            )

        for index, value in enumerate(self.saved):
            if matches(value):
                return self.saved.pop(index)
        while time.monotonic() < deadline:
            value = self.output.get(timeout=max(0.01, deadline - time.monotonic()))
            if matches(value):
                return value
            self.saved.append(value)
        raise TimeoutError("Fixture response deadline")

    def call(self, method, params=None):
        self.counter += 1
        self.send({"jsonrpc": "2.0", "id": self.counter, "method": method, "params": params or {}})
        return self.receive(self.counter)

    def initialize(self):
        value = self.call(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        )
        assert value["result"]["serverInfo"]["version"] == "0.2.8"
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def state(self):
        try:
            return read_json(self.root / "bridge-state.json")
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def wait_state(self, predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = self.state()
            if predicate(value):
                return value
            time.sleep(0.02)
        raise AssertionError(self.state())

    def close(self, expected_code=0):
        (self.root / "release-block").touch()
        (self.root / "release-listen").touch()
        if not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            code = self.process.wait(timeout=8)
        finally:
            self.errors.close()
        self.reader.join(timeout=1)
        self.process.stdout.close()
        assert code == expected_code


@pytest.fixture
def host(store):
    value = Host(store.root)
    try:
        yield value
    finally:
        value.close()


def test_id_domain_matches_pinned_sdk():
    assert message_key("7") == message_key(7) == message_key(" +007 ")
    for value in (None, True, 1.2):
        with pytest.raises(ValueError):
            message_key(value)


def test_nullable_optional_params_match_sdk():
    value = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": None}
    validate_message(value)
    assert value["params"] == {}


def test_malformed_initialization_fails_closed_without_exception(store):
    broker = Broker([], store.root, "0.2.8", stdout=io.BytesIO())
    try:
        for result in (
            {"serverInfo": "bad"},
            {"serverInfo": {"version": "0.2.8"}, "capabilities": []},
            {"serverInfo": {"version": "0.2.8"}, "capabilities": {"resources": True}},
        ):
            assert not broker._initialization_matches(result)
    finally:
        broker.guard.close()


def test_callback_cancel_uses_sdk_id_domain_and_current_generation(store):
    output = io.BytesIO()
    broker = Broker([], store.root, "0.2.8", stdout=output)
    broker.protocol_mode = "legacy"
    broker.generation = 3
    broker.reverse[message_key("rewritten")] = {"original_id": 7, "generation": 3}
    try:
        broker._backend(
            {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": "7"}}, None
        )
        assert json.loads(output.getvalue())["params"]["requestId"] == "rewritten"
    finally:
        broker.guard.close()


def test_idle_then_call_reuses_outer_pipe_and_wakes_once(host):
    host.initialize()
    host.wait_state(lambda s: s.get("phase") == "cold")
    assert host.call("ping")["result"] == {}
    assert host.state()["backend_generation"] == 1
    answer = host.call("tools/call", {"name": "increment", "arguments": {}})
    assert answer["result"] == {"value": 1}
    assert host.state()["backend_generation"] == 2
    assert (host.root / "fixture-starts.txt").read_text().splitlines() == ["start", "start"]


def test_keepalive_ping_does_not_prevent_idle(host):
    host.initialize()
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        assert host.call("ping")["result"] == {}
        if host.state().get("phase") == "cold":
            break
        time.sleep(0.03)
    assert host.state()["phase"] == "cold"


def test_concurrent_wake_dispatches_each_request_once(host):
    host.initialize()
    host.wait_state(lambda s: s.get("phase") == "cold")
    for identifier in range(1, 17):
        host.send(
            {
                "jsonrpc": "2.0",
                "id": identifier,
                "method": "tools/call",
                "params": {"name": "echo", "arguments": {"sequence": identifier}},
            }
        )
    for identifier in range(1, 17):
        assert host.receive(identifier)["result"]["echo"] == {"sequence": identifier}
    assert host.state()["backend_generation"] == 2


def test_crash_after_effect_is_unknown_and_never_replayed(host):
    host.initialize()
    failure = host.call("tools/call", {"name": "crash_after_increment"})
    assert failure["error"]["data"] == {"origin_outcome": "UNKNOWN", "retry_safe": False}
    host.wait_state(lambda s: not s.get("backend_alive", True))
    assert host.call("tools/call", {"name": "read_counter"})["result"] == {"value": 1}
    time.sleep(0.4)
    assert host.state()["backend_alive"]
    assert "backend_exit_with_request" in host.state()["retained_reasons"]


def test_inflight_and_progress_protect_backend(host):
    host.initialize()
    assert host.call("tools/call", {"name": "progress"})["result"] == {"done": True}
    host.send({"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "block"}})
    host.wait_state(lambda s: s.get("inflight") == 1)
    time.sleep(0.5)
    assert host.state()["backend_generation"] == 1
    assert host.state()["backend_alive"]
    (host.root / "release-block").touch()
    assert host.receive(10)["result"] == {"done": True}


def test_callback_has_generation_safe_id_and_prevents_idle(host):
    host.initialize()
    host.send({"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "callback"}})
    callback = host.receive(method="roots/list")
    assert callback["id"] != 7
    time.sleep(0.4)
    assert host.state()["reverse_requests"] == 1
    host.send({"jsonrpc": "2.0", "id": callback["id"], "result": {"roots": []}})
    assert host.receive(10)["result"] == {"callback_finished": True}
    host.wait_state(lambda s: s.get("phase") == "cold")
    host.send({"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "callback"}})
    second = host.receive(method="roots/list")
    assert second["id"] != callback["id"]
    host.send({"jsonrpc": "2.0", "id": callback["id"], "result": {"roots": []}})
    host.wait_state(lambda s: "unmatched_client_response" in s.get("retained_reasons", []))
    assert host.state()["reverse_requests"] == 1
    host.send({"jsonrpc": "2.0", "id": second["id"], "result": {"roots": []}})
    assert host.receive(11)["result"]["callback_finished"]


@pytest.mark.parametrize("kind", ["error", "cancel", "notification"])
def test_uncertain_protocol_state_pins_worker(host, kind):
    host.initialize()
    if kind == "error":
        assert host.call("tools/call", {"name": "error"})["result"]["isError"]
    else:
        method = "notifications/cancelled" if kind == "cancel" else "notifications/unknown-extension"
        host.send({"jsonrpc": "2.0", "method": method, "params": {"requestId": 99}})
    time.sleep(0.6)
    assert host.state()["backend_generation"] == 1
    assert host.state()["backend_alive"]
    assert host.state()["retained_reasons"]


def test_modern_discover_and_continuation_transparently_retain_backend(host):
    meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}
    discovery = host.call("server/discover", {"_meta": meta})["result"]
    assert discovery["_meta"]["io.modelcontextprotocol/serverInfo"]["version"] == "0.2.8"
    continuation = host.call("tools/call", {"name": "input_required", "_meta": meta})["result"]
    assert continuation["resultType"] == "input_required"
    time.sleep(0.6)
    assert (
        host.call(
            "tools/call",
            {"name": "echo", "arguments": {"inputResponses": {}, "requestState": "opaque"}, "_meta": meta},
        )["result"]["echo"]["requestState"]
        == "opaque"
    )
    assert host.state()["backend_generation"] == 1
    assert host.state()["protocol_mode"] == "passthrough"


def test_listen_ack_does_not_complete_exchange(host):
    host.call("server/discover", {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}})
    host.send({"jsonrpc": "2.0", "id": 8, "method": "subscriptions/listen", "params": {}})
    host.receive(method="notifications/subscriptions/acknowledged")
    time.sleep(0.4)
    assert host.state()["inflight"] == 1
    (host.root / "release-listen").touch()
    assert host.receive(8)["result"]["resultType"] == "complete"


def test_request_arriving_during_barrier_is_not_lost(host):
    (host.root / "barrier-delay").write_text("0.3")
    host.initialize()
    host.wait_state(lambda s: s.get("phase") == "preparing")
    assert host.call("tools/call", {"name": "increment"})["result"] == {"value": 1}
    assert host.state()["backend_generation"] == 1


def test_request_waits_for_retiring_owner_before_new_spawn(host):
    (host.root / "eof-delay").write_text("0.4")
    host.initialize()
    host.wait_state(lambda s: s.get("phase") == "retiring")
    assert host.call("tools/call", {"name": "increment"})["result"] == {"value": 1}
    assert host.state()["backend_generation"] == 2


def test_eof_drains_inflight_call_without_terminating_worker(host):
    host.initialize()
    host.send({"jsonrpc": "2.0", "id": 20, "method": "tools/call", "params": {"name": "block"}})
    host.wait_state(lambda s: s.get("inflight") == 1)
    host.process.stdin.close()
    time.sleep(0.3)
    assert host.process.poll() is None
    (host.root / "release-block").touch()
    assert host.receive(20)["result"]["done"]
    assert host.process.wait(timeout=5) == 0


def test_large_response_is_preserved(host):
    host.initialize()
    assert host.call("tools/call", {"name": "large"})["result"]["data"] == "x" * (512 * 1024)
    host.wait_state(lambda s: s.get("phase") == "cold")


def test_wire_retries_short_writes_and_does_not_assume_success(store):
    class ShortWriter(io.BytesIO):
        def write(self, data):
            return super().write(data[:3])

    output = ShortWriter()
    broker = Broker([], store.root, "0.2.8", stdout=output)
    try:
        broker._wire(output, {"jsonrpc": "2.0", "id": 1, "result": {}})
        assert json.loads(output.getvalue())["result"] == {}
    finally:
        broker.guard.close()


def test_partial_write_failure_retains_unknown_execution(store):
    class BrokenWriter:
        def write(self, data):
            raise BrokenPipeError

    broker = Broker([], store.root, "0.2.8", stdout=io.BytesIO())

    class Worker:
        stdin = BrokenWriter()

    broker.process = Worker()
    try:
        broker._forward({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {}})
        assert message_key(2) in broker.uncertain_inflight
        assert json.loads(broker.stdout.getvalue())["error"]["data"]["origin_outcome"] == "UNKNOWN"
    finally:
        broker.guard.close()


def test_failed_output_is_known_complete_but_not_delivered(store):
    class BrokenWriter:
        def write(self, data):
            raise BrokenPipeError

    broker = Broker([], store.root, "0.2.8", stdout=BrokenWriter())
    key = message_key(9)
    broker.pending[key] = {"id": 9, "method": "tools/call"}
    broker.admitted.add(key)
    try:
        broker._backend({"jsonrpc": "2.0", "id": 9, "result": {}}, None)
        assert not broker.pending
        assert key in broker.undelivered
        assert broker.output_closed and broker.input_closed
        assert "output_delivery_failed" in broker.pins
    finally:
        broker.guard.close()


def test_uncertain_id_cannot_be_reused_before_owner_exits(store):
    broker = Broker([], store.root, "0.2.8", stdout=io.BytesIO())
    broker.uncertain_inflight.add(message_key(7))
    try:
        request = {"jsonrpc": "2.0", "id": "7", "method": "tools/call", "params": {}}
        broker._host(request, json.dumps(request).encode() + b"\n")
        assert broker.process is None
        assert "duplicate_request_id" in broker.pins
        assert json.loads(broker.stdout.getvalue())["id"] is None
    finally:
        broker.guard.close()


def test_duplicate_id_does_not_replace_inflight_execution(host):
    host.initialize()
    host.send({"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "block"}})
    host.wait_state(lambda s: s.get("inflight") == 1)
    host.send({"jsonrpc": "2.0", "id": "7", "method": "tools/call", "params": {"name": "increment"}})
    assert host.receive(None)["error"]["code"] == -32600
    assert not (host.root / "fixture-counter").exists()
    (host.root / "release-block").touch()
    assert host.receive(7)["result"]["done"]


def test_cancel_without_terminal_response_keeps_ownership_after_eof(store):
    class Worker:
        stdin = io.BytesIO()

    broker = Broker([], store.root, "0.2.8", stdout=io.BytesIO())
    broker.process = Worker()
    broker.pending[message_key(1)] = {"id": 1, "method": "tools/call"}
    try:
        broker._pin("cancellation_observed")
        broker._eof()
        broker._tick()
        assert not broker.process.stdin.closed
        assert broker.pending
    finally:
        broker.guard.close()


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"result": []},
        {"result": {}, "error": {}},
        {"error": {"code": True, "message": "bad"}},
        {"error": {"code": -1}},
        {"method": "tools/call", "result": {}},
        {"params": {}, "result": {}},
    ],
)
def test_malformed_terminal_envelope_rejected(extra):
    with pytest.raises(ValueError):
        validate_message({"jsonrpc": "2.0", "id": 1, **extra})


def test_malformed_backend_response_does_not_settle_execution_on_eof(store):
    host = Host(store.root)
    try:
        host.initialize()
        host.send(
            {"jsonrpc": "2.0", "id": 20, "method": "tools/call", "params": {"name": "malformed_then_block"}}
        )
        host.wait_state(lambda s: "protocol_message_unconfirmed" in s.get("retained_reasons", []))
        assert host.state()["inflight"] == 1
        host.process.stdin.close()
        time.sleep(0.3)
        assert host.process.poll() is None
        (host.root / "release-block").touch()
        assert host.receive(20)["result"]["done"]
    finally:
        host.close(expected_code=1)


def test_malformed_callback_reply_does_not_settle_reverse_request(store):
    host = Host(store.root)
    try:
        host.initialize()
        host.send({"jsonrpc": "2.0", "id": 20, "method": "tools/call", "params": {"name": "callback"}})
        callback = host.receive(method="roots/list")
        host.send({"jsonrpc": "2.0", "id": callback["id"]})
        assert host.receive(None)["error"]["code"] == -32600
        host.wait_state(lambda s: "protocol_message_unconfirmed" in s.get("retained_reasons", []))
        assert host.state()["reverse_requests"] == 1
        host.send({"jsonrpc": "2.0", "id": callback["id"], "result": {"roots": []}})
        assert host.receive(20)["result"]["callback_finished"]
    finally:
        host.close(expected_code=1)


def test_cancel_while_waiting_never_dispatches_scientific_request(host):
    (host.root / "barrier-delay").write_text("0.5")
    host.initialize()
    host.wait_state(lambda s: s.get("phase") == "preparing")
    host.send({"jsonrpc": "2.0", "id": 30, "method": "tools/call", "params": {"name": "increment"}})
    host.send({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": "30"}})
    host.wait_state(lambda s: s.get("phase") == "active")
    assert host.call("tools/call", {"name": "read_counter"})["result"]["value"] == 0
    host.wait_state(lambda s: s.get("inflight") == 0)
    assert all(value.get("id") != 30 for value in host.saved)


def test_callback_arriving_after_host_eof_receives_terminal_error(host):
    host.initialize()
    host.send({"jsonrpc": "2.0", "id": 31, "method": "tools/call", "params": {"name": "late_callback"}})
    host.wait_state(lambda s: s.get("inflight") == 1)
    host.process.stdin.close()
    assert host.receive(31)["result"]["callback_finished"]
    assert not any(value.get("method") == "roots/list" for value in host.saved)
    assert host.process.wait(timeout=5) == 0


def test_idle_lease_fences_jobs_sessions_and_unknown_state(store):
    control = IdleControl(store.root, "x" * 32)
    prepare = {"token": "x" * 32, "action": "prepare"}
    try:
        with file_lock(store.root / "device.lock", timeout=0):
            assert not control.handle(prepare)["allowed"]
        with sqlite3.connect(store.root / "queue.sqlite3") as db:
            db.execute("CREATE TABLE jobs (state TEXT)")
            db.execute("INSERT INTO jobs VALUES ('running')")
        assert control.handle(prepare)["reason"] == "scientific_work_pending"
        with sqlite3.connect(store.root / "queue.sqlite3") as db:
            db.execute("DELETE FROM jobs")
        session = store.root / "sessions" / ("a" * 32) / "session.json"
        write_json(session, {"state": "ready", "gui_transaction": {"phase": "open"}})
        assert control.handle(prepare)["reason"] == "session_work_pending"
        write_json(session, {"state": "needs_attention"})
        assert not control.handle(prepare)["allowed"]
        write_json(session, {"state": "closed"})
        answer = control.handle(prepare)
        assert answer["allowed"]
        assert control.handle({**prepare, "action": "commit", "lease": answer["lease"]})["allowed"]
        called = []
        assert control.retire(lambda: called.append(True))
        assert called == [True]
    finally:
        control.close()


def test_expired_lease_cannot_close_owned_pipe(store):
    now = [10.0]
    control = IdleControl(store.root, "x" * 32, clock=lambda: now[0], lease_seconds=1)
    try:
        answer = control.handle({"token": "x" * 32, "action": "prepare"})
        control.handle({"token": "x" * 32, "action": "commit", "lease": answer["lease"]})
        now[0] = 12
        assert not control.retire(lambda: pytest.fail("Expired lease closed a pipe"))
        with file_lock(store.root / "device.lock", timeout=0):
            pass
    finally:
        control.close()
