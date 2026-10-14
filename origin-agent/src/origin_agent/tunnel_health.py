"""Bounded, credential-free observation of the exact owned client's control plane."""

import json
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import psutil


class HealthOwnershipError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def timestamp(value):
    if not isinstance(value, str) or len(value) > 48:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo else None
    except (ValueError, OverflowError, OSError):
        return None


def unknown(reason="remote_health_unavailable"):
    return {"state": "unknown", "reason": reason, "observed_epoch": time.time(), "idle": False}


def classify(snapshot, created, *, now=None):
    now = time.time() if now is None else now
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
        return unknown("remote_health_invalid")
    observed = timestamp(snapshot.get("snapshot_at"))
    runtime = snapshot.get("runtime") or {}
    started = timestamp(runtime.get("started_at"))
    if observed is None or not -5 <= now - observed <= 15:
        return unknown("remote_health_stale")
    if started is None or abs(started - created) > 2:
        raise HealthOwnershipError("remote_health_identity_conflict")
    components = snapshot.get("components") or {}
    control = components.get("control-plane") or {}
    details = control.get("details") or {}
    success = timestamp(details.get("last_success"))
    attempt = timestamp(details.get("last_attempt"))
    failure = timestamp(details.get("last_error"))
    retry = timestamp(details.get("next_retry"))
    deadline = details.get("deadline_seconds", 35)
    if not isinstance(deadline, (int, float)) or not 1 <= deadline <= 300:
        return unknown("remote_health_invalid")
    threshold = max(90, 2 * deadline + 10)
    code = details.get("http_status")
    code = code if type(code) is int and 100 <= code <= 599 else None
    pending = []
    for component, field in (
        ("dispatcher", "active"),
        ("queue", "depth"),
        ("response-delivery", "in_progress"),
    ):
        value = (components.get(component, {}).get("details") or {}).get(field)
        pending.append(type(value) is int and value == 0)
    result = {
        "state": "recovering",
        "reason": "control_plane_recovering",
        "observed_epoch": now,
        "last_success_epoch": success,
        "last_attempt_epoch": attempt,
        "last_error_epoch": failure,
        "next_retry_at": retry,
        "http_status": code,
        "idle": all(pending),
    }
    if code in (401, 403) and failure is not None and (success is None or failure >= success):
        result.update(state="authentication_required", reason="authentication_required")
    elif (
        control.get("state") != "backoff"
        and success is not None
        and (failure is None or success > failure)
        and -5 <= now - success <= threshold
    ):
        result.update(state="online", reason=None)
    elif now - max(started, attempt or started, failure or started, success or started) > threshold:
        if retry is None or now > retry + threshold:
            result.update(state="stalled", reason="control_plane_stalled")
    return result


def read_remote(connection, daemon, timeout=3):
    """Use the scoped health file and a listener owned by the verified daemon.

    No credentials, environment proxy, redirects, remote URLs, log tails, or
    active MCP calls enter this read-only path. Unknown observations never
    authorize terminating a connector or replaying work.
    """
    if connection.client_state_dir is None:
        return unknown()
    path = connection.client_state_dir / "health" / (connection.alias + ".url")
    try:
        if path.resolve() != path or path.stat().st_size > 512:
            raise HealthOwnershipError("remote_health_endpoint_conflict")
        parsed = urlsplit(path.read_text(encoding="utf-8").strip())
        if (
            parsed.scheme != "http"
            or parsed.hostname not in ("127.0.0.1", "::1")
            or not parsed.port
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise HealthOwnershipError("remote_health_endpoint_conflict")
        if not daemon.live():
            return unknown()
        listeners = psutil.Process(daemon.pid).net_connections(kind="tcp")
        if not any(c.status == psutil.CONN_LISTEN and c.laddr.port == parsed.port for c in listeners):
            raise HealthOwnershipError("remote_health_endpoint_conflict")
        opener = build_opener(ProxyHandler({}), NoRedirect())
        request = Request(
            f"http://{parsed.netloc}/health?details=true", headers={"Accept": "application/json"}
        )
        with opener.open(request, timeout=timeout) as response:
            data = response.read(65537)
        if len(data) > 65536:
            return unknown("remote_health_invalid")
        if not daemon.live():
            return unknown()
        return classify(json.loads(data), daemon.created)
    except HealthOwnershipError:
        raise
    except (OSError, ValueError, TypeError, AttributeError, URLError, HTTPError, psutil.Error):
        return unknown()
