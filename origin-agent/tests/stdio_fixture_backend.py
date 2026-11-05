"""Synthetic subprocess only; no Origin, SDK, scientific queue or native job."""

import json
import os
import sys
import threading
import time
from pathlib import Path

root = Path(os.environ["ORIGIN_AGENT_HOME"])
lock = threading.Lock()
callbacks = {}
threads = []
with (root / "fixture-starts.txt").open("a") as stream:
    stream.write("start\n")


def send(value):
    with lock:
        sys.stdout.write(json.dumps(value) + "\n")
        sys.stdout.flush()


def result(identifier, value):
    send({"jsonrpc": "2.0", "id": identifier, "result": value})


def execute(message):
    identifier = message["id"]
    method = message["method"]
    params = message.get("params", {})
    if method == "initialize":
        result(
            identifier,
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "origin-agent", "version": "0.2.8"},
                "instructions": "fixture",
            },
        )
    elif method == "server/discover":
        result(
            identifier,
            {
                "supportedVersions": ["2026-07-28"],
                "capabilities": {"tools": {}},
                "ttlMs": 0,
                "cacheScope": "private",
                "resultType": "complete",
                "_meta": {"io.modelcontextprotocol/serverInfo": {"name": "origin-agent", "version": "0.2.8"}},
            },
        )
    elif method == "ping":
        delay = root / "barrier-delay"
        if delay.exists():
            time.sleep(float(delay.read_text()))
        result(identifier, {})
    elif method == "subscriptions/listen":
        send(
            {
                "jsonrpc": "2.0",
                "method": "notifications/subscriptions/acknowledged",
                "params": {
                    "notifications": {},
                    "_meta": {"io.modelcontextprotocol/subscriptionId": identifier},
                },
            }
        )
        while not (root / "release-listen").exists():
            time.sleep(0.01)
        result(identifier, {"resultType": "complete"})
    elif method == "tools/call":
        name = params["name"]
        if name in {"increment", "crash_after_increment"}:
            path = root / "fixture-counter"
            value = int(path.read_text()) if path.exists() else 0
            path.write_text(str(value + 1))
            if name == "crash_after_increment":
                os._exit(23)
            result(identifier, {"value": value + 1})
        elif name == "read_counter":
            path = root / "fixture-counter"
            result(identifier, {"value": int(path.read_text()) if path.exists() else 0})
        elif name in {"block", "malformed_then_block"}:
            if name == "malformed_then_block":
                send({"jsonrpc": "2.0", "id": identifier})
            (root / "block-entered").write_text("yes")
            while not (root / "release-block").exists():
                time.sleep(0.01)
            result(identifier, {"done": True})
        elif name in {"callback", "late_callback"}:
            if name == "late_callback":
                time.sleep(0.3)
            event = threading.Event()
            callbacks[7] = event
            send({"jsonrpc": "2.0", "id": 7, "method": "roots/list", "params": {}})
            event.wait(5)
            result(identifier, {"callback_finished": event.is_set()})
        elif name == "progress":
            for count in range(3):
                send(
                    {
                        "jsonrpc": "2.0",
                        "method": "notifications/progress",
                        "params": {
                            "progressToken": "test-progress",
                            "progress": count,
                        },
                    }
                )
                time.sleep(0.1)
            result(identifier, {"done": True})
        elif name == "large":
            result(identifier, {"data": "x" * (512 * 1024)})
        elif name == "input_required":
            result(
                identifier, {"resultType": "input_required", "inputRequests": {}, "requestState": "opaque"}
            )
        elif name == "error":
            result(identifier, {"isError": True, "content": [{"type": "text", "text": "fixture failure"}]})
        else:
            result(identifier, {"echo": params.get("arguments", {})})
    else:
        result(identifier, {})


for line in sys.stdin:
    message = json.loads(line)
    if "method" not in message:
        callback = callbacks.pop(message.get("id"), None)
        if callback:
            callback.set()
    elif "id" in message:
        worker = threading.Thread(target=execute, args=(message,))
        threads.append(worker)
        worker.start()
for worker in threads:
    worker.join()
delay = root / "eof-delay"
if delay.exists():
    time.sleep(float(delay.read_text()))
