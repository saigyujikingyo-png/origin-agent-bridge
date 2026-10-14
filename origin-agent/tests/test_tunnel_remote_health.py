import json
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import psutil
import pytest

from origin_agent.tunnel_health import HealthOwnershipError, classify, read_remote
from origin_agent.tunnel_lifecycle import Identity


def iso(epoch):
    return datetime.fromtimestamp(epoch, UTC).isoformat()


def snapshot(now, created, *, success=None, failure=None, attempt=None, code=None, state="polling", busy=0):
    return {
        "schema_version": 1,
        "snapshot_at": iso(now),
        "runtime": {"started_at": iso(created)},
        "components": {
            "control-plane": {
                "state": state,
                "status": "ok",
                "details": {
                    "last_success": iso(success) if success else None,
                    "last_error": iso(failure) if failure else None,
                    "last_attempt": iso(attempt) if attempt else None,
                    "http_status": code,
                    "deadline_seconds": 35,
                },
            },
            "dispatcher": {"details": {"active": busy}},
            "queue": {"details": {"depth": 0}},
            "response-delivery": {"details": {"in_progress": 0}},
        },
    }


@pytest.mark.parametrize("code", [401, 403])
def test_local_ready_does_not_mask_rejected_credentials(code):
    data = snapshot(1000, 800, attempt=999, failure=999, code=code, state="backoff")
    data.update(ready=True, live=True)
    observed = classify(data, 800, now=1000)
    assert observed["state"] == "authentication_required"
    assert observed["http_status"] == code


def test_recovered_auth_error_does_not_block_a_newer_success():
    data = snapshot(1000, 800, success=999, failure=900, code=401)
    assert classify(data, 800, now=1000)["state"] == "online"


def test_long_outage_with_active_retries_is_preserved():
    data = snapshot(5000, 800, success=900, failure=4999, attempt=4998, state="backoff")
    assert classify(data, 800, now=5000)["state"] == "recovering"


def test_hung_poll_is_distinguished_from_a_live_retry_and_busy_work():
    data = snapshot(1000, 100, success=200, attempt=201)
    observed = classify(data, 100, now=1000)
    assert observed["state"] == "stalled" and observed["idle"]
    data["components"]["dispatcher"]["details"]["active"] = 1
    assert not classify(data, 100, now=1000)["idle"]
    data["components"]["control-plane"]["details"]["next_retry"] = iso(2000)
    assert classify(data, 100, now=1000)["state"] == "recovering"


def test_stale_or_wrong_generation_snapshot_never_reports_online():
    data = snapshot(1000, 800, success=999)
    assert classify(data, 800, now=1040)["state"] == "unknown"
    with pytest.raises(HealthOwnershipError):
        classify(data, 500, now=1000)


@pytest.fixture
def local_health(tmp_path):
    behavior = {"redirect": False, "large": False}
    owner = Identity.capture(psutil.Process(), "daemon")
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append((self.path, self.headers.get("Authorization")))
            if behavior["redirect"]:
                self.send_response(302)
                self.send_header("Location", "/never-follow")
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
            now = time.time()
            data = snapshot(now, owner.created, success=now - 1, attempt=now)
            data["private_unexpected"] = "sk-never-copy-me"
            self.wfile.write(b"x" * 65537 if behavior["large"] else json.dumps(data).encode())

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = SimpleNamespace(client_state_dir=tmp_path, alias="fixture")
    path = tmp_path / "health/fixture.url"
    path.parent.mkdir()
    path.write_text(f"http://127.0.0.1:{server.server_port}")
    try:
        yield connection, owner, behavior, calls, path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


def test_health_read_is_bounded_passive_and_does_not_forward_secrets(local_health, monkeypatch):
    c, owner, behavior, calls, _ = local_health
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "sk-not-for-health")
    value = read_remote(c, owner)
    assert value["state"] == "online"
    assert "sk-" not in json.dumps(value)
    assert calls == [("/health?details=true", None)]
    behavior["redirect"] = True
    assert read_remote(c, owner)["state"] == "unknown"
    assert not any(path == "/never-follow" for path, _ in calls)
    behavior.update(redirect=False, large=True)
    assert read_remote(c, owner)["state"] == "unknown"


@pytest.mark.parametrize("url", ["http://example.com/", "http://127.0.0.1:1", "http://user@127.0.0.1:9"])
def test_health_endpoint_must_belong_to_exact_daemon(local_health, url):
    c, owner, _, _, path = local_health
    path.write_text(url)
    with pytest.raises(HealthOwnershipError):
        read_remote(c, owner)


def test_retry_in_progress_does_not_reuse_success_from_before_network_failure():
    data = snapshot(1000, 800, success=997, failure=998, attempt=999, state="polling")
    assert classify(data, 800, now=1000)["state"] == "recovering"
    data["components"]["control-plane"]["details"]["last_success"] = iso(1000)
    assert classify(data, 800, now=1000)["state"] == "online"
