"""Bounded, profile-scoped supervision. Never owns native or durable job workers."""

import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path

import psutil

from .storage import BusyError, file_lock, write_json


class LifecycleError(RuntimeError):
    """Messages are stable sanitized codes, never raw CLI output/credentials."""


class OwnershipError(LifecycleError):
    pass


class StopRequested(LifecycleError):
    pass


def canonical(path):
    return os.path.normcase(str(Path(path).resolve()))


def read(path, default=None):
    if not Path(path).exists():
        return default
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def utc():
    return datetime.now(UTC).isoformat()


def option(argv, flag):
    values = [arg.split("=", 1)[1] for arg in argv if arg.startswith(flag + "=")]
    values += [argv[i + 1] for i, arg in enumerate(argv[:-1]) if arg == flag]
    if len(values) > 1:
        raise OwnershipError("ambiguous_command_arguments")
    return values[0] if values else None


@dataclass(frozen=True)
class Connection:
    alias: str
    profile: str
    profile_dir: Path
    cloud_root: Path
    state_root: Path
    secret_file: Path
    tunnel_client: Path

    @classmethod
    def load(cls, path):
        value = read(path)
        if value.get("schema_version") != 1:
            raise LifecycleError("unsupported_connection_config")
        for name in ("alias", "profile"):
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value[name]):
                raise LifecycleError("invalid_connection_name")
        paths = {}
        for name in ("profile_dir", "cloud_root", "state_root", "secret_file", "tunnel_client"):
            if not Path(value[name]).is_absolute():
                raise LifecycleError("absolute_connection_paths_required")
            paths[name] = Path(value[name]).resolve()
        if paths["profile_dir"].parent != paths["cloud_root"]:
            raise LifecycleError("profile_directory_outside_connection")
        if not paths["cloud_root"].is_relative_to(paths["state_root"] / "cloud"):
            raise LifecycleError("connection_outside_state_root")
        return cls(alias=value["alias"], profile=value["profile"], **paths)

    @cached_property
    def engine(self):
        return Path(read(self.state_root / "install.json")["executable"]).resolve()

    @cached_property
    def scope(self):
        value = f"{psutil.Process().username()}\n{canonical(self.profile_dir)}\n{self.profile}"
        return hashlib.sha256(value.encode()).hexdigest()

    @property
    def lock(self):
        # Put the lock beside the canonical profile, so alternate config paths share it.
        return self.profile_dir / f".origin-{self.profile}.lock"

    @property
    def profile_path(self):
        return self.profile_dir / f"{self.profile}.yaml"

    def intent(self):
        return read(self.cloud_root / "intent.json", {"enabled": True, "stop_requested": False})


@dataclass(frozen=True)
class Identity:
    pid: int
    created: float
    exe: str
    user: str
    parent_pid: int
    parent_created: float | None
    role: str

    @classmethod
    def capture(cls, process, role):
        with process.oneshot():
            parent_pid = process.ppid()
            try:
                parent_created = psutil.Process(parent_pid).create_time()
            except psutil.NoSuchProcess:
                parent_created = None
            return cls(
                process.pid,
                process.create_time(),
                canonical(process.exe()),
                process.username(),
                parent_pid,
                parent_created,
                role,
            )

    def live(self):
        try:
            p = psutil.Process(self.pid)
            return (
                p.is_running()
                and p.status() != psutil.STATUS_ZOMBIE
                and abs(p.create_time() - self.created) < 0.001
                and canonical(p.exe()) == self.exe
                and p.username() == self.user
            )
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied as exc:
            raise OwnershipError("process_identity_inaccessible") from exc


@dataclass(frozen=True)
class Policy:
    command_timeout: float = 20
    ready_timeout: float = 90
    poll: float = 0.25
    health_interval: float = 15
    stale_after: float = 40
    cleanup_timeout: float = 8
    retries: tuple = (5, 15, 30)


class Controller:
    def __init__(self, connection, *, policy=None, command=None):
        self.c = connection
        self.policy = policy or Policy()
        self.command = command or [str(connection.tunnel_client)]
        self.user = psutil.Process().username()
        self.owner = Identity.capture(psutil.Process(), "supervisor")
        self.ledger_path = self.c.cloud_root / "ownership.json"
        saved = read(self.ledger_path, {})
        if saved and saved.get("scope") != self.c.scope:
            raise OwnershipError("ownership_scope_conflict")
        self.known = [Identity(**item) for item in saved.get("processes", [])]
        self.attempt = saved.get("attempt")

    def save(self):
        value = {"scope": self.c.scope, "attempt": self.attempt, "processes": [asdict(p) for p in self.known]}
        before = read(self.ledger_path, {})
        if any(before.get(key) != item for key, item in value.items()):
            write_json(self.ledger_path, {**value, "observed_at": utc()})

    def note(self, phase, *, reason=None, ready=False, healthy=False, daemon=None):
        now = time.time()
        value = {
            "schema_version": 1,
            "scope": self.c.scope,
            "state": phase,
            "observed_at": utc(),
            "observed_epoch": now,
            "valid_until": now + self.policy.stale_after,
            "reason": reason,
            "ready": ready,
            "healthy": healthy,
            "supervisor": asdict(self.owner),
            "daemon": asdict(daemon) if daemon else None,
        }
        write_json(self.c.cloud_root / "supervisor-state.json", value)
        # Invalidate the old launcher's success receipt for readers of the legacy path too.
        write_json(self.c.cloud_root / "background-status.json", value)
        return value

    def check_stop(self):
        intent = self.c.intent()
        if not intent.get("enabled", True) or intent.get("stop_requested", False):
            raise StopRequested("stop_requested")

    def pause(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.check_stop()
            time.sleep(min(self.policy.poll, max(0, end - time.monotonic())))

    def _daemon(self, process):
        argv = process.cmdline()
        profile = option(argv, "--profile")
        directory = option(argv, "--profile-dir")
        if "run" not in argv:
            return False
        if profile != self.c.profile:
            return False
        if not directory or canonical(directory) != canonical(self.c.profile_dir):
            # Alias metadata is user-global in tunnel-client. Do not overwrite a collision.
            raise OwnershipError("profile_directory_conflict")
        if canonical(process.exe()) != canonical(self.c.tunnel_client) or process.username() != self.user:
            raise OwnershipError("daemon_executable_or_user_conflict")
        return True

    def scan(self):
        """Discover missing-registry owners; only persist children with observed parent identities."""
        daemons, frontends = [], []
        possible_frontends = []
        for p in psutil.process_iter(["name"]):
            # Exclude other applications before accessing command lines or protected processes.
            if p.info["name"].lower() not in {self.c.tunnel_client.name.lower(), self.c.engine.name.lower()}:
                continue
            try:
                if p.username() != self.user:
                    continue
                if self._daemon(p):
                    daemons.append(Identity.capture(p, "daemon"))
                elif canonical(p.exe()) == canonical(self.c.engine) and "serve" in p.cmdline():
                    if p.username() == self.user:
                        possible_frontends.append(p)
            except psutil.NoSuchProcess:
                continue
            except psutil.AccessDenied as exc:
                raise OwnershipError("candidate_process_inaccessible") from exc
        owners = {d.pid: d for d in daemons}
        pending = possible_frontends
        # PyInstaller may have one same-executable launch shim; it is one linear server chain.
        while pending:
            progress, rest = False, []
            for p in pending:
                try:
                    item = Identity.capture(p, "frontend")
                    parent = owners.get(item.parent_pid)
                    if (
                        parent
                        and item.parent_created == parent.created
                        and item.created >= parent.created
                        and parent.live()
                    ):
                        frontends.append(item)
                        owners[item.pid] = item
                        progress = True
                    else:
                        rest.append(p)
                except psutil.NoSuchProcess:
                    continue
            if not progress:
                pending = rest
                break
            pending = rest
        known_live = [p for p in self.known if p.live()]
        # An orphan without a previously observed lineage cannot be claimed from its PID/name.
        for p in pending:
            try:
                item = Identity.capture(p, "frontend")
                if item.parent_pid <= 1 or item.parent_created is None or item.parent_created > item.created:
                    if not any(k.pid == item.pid and k.created == item.created for k in known_live):
                        raise OwnershipError("unproven_orphan_frontend")
            except psutil.NoSuchProcess:
                continue
        combined = {(p.pid, p.created): p for p in known_live + daemons + frontends}
        self.known = list(combined.values())
        self.save()
        return daemons, [p for p in self.known if p.role == "frontend"]

    def command_json(self, args, *, timeout=None, observe=False, stopping=False):
        """No shell, hard deadline, no raw diagnostics returned or written to receipts."""
        environment = os.environ.copy()
        if args[:2] != ["runtimes", "connect"]:
            environment.pop("CONTROL_PLANE_API_KEY", None)
        proc = subprocess.Popen(
            self.command + args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.monotonic() + (timeout or self.policy.command_timeout)
        try:
            while True:
                if not stopping:
                    self.check_stop()
                if observe:
                    self.scan()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise LifecycleError("command_timeout")
                try:
                    out, err = proc.communicate(timeout=min(self.policy.poll, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            if proc.returncode:
                # Official tunnel-client v0.0.14 uses this exact diagnostic for a
                # never-registered alias. This is absence, not a generic status failure.
                absent = f"alias {self.c.alias} is not known; run create or connect first".encode()
                if (
                    proc.returncode == 1
                    and args == ["runtimes", "status", self.c.alias, "--json"]
                    and (out + err).strip() == absent
                ):
                    return {"alias_missing": True}
                lower = err.lower()
                if any(x in lower for x in (b"unauthorized", b"forbidden", b"invalid api key")):
                    raise LifecycleError("authentication_required")
                raise LifecycleError("command_failed")
            if len(out) > 2 * 1024 * 1024:
                raise LifecycleError("status_output_too_large")
            try:
                value = json.loads(out)
            except (ValueError, UnicodeDecodeError) as exc:
                raise LifecycleError("invalid_command_output") from exc
            # Reserved internal marker: successful vendor JSON cannot claim absence
            # or bypass the profile checks in probe().
            if not isinstance(value, dict) or "alias_missing" in value:
                raise LifecycleError("invalid_command_output")
            return value
        finally:
            if proc.poll() is None:
                proc.kill()  # Only our still-live Popen command, never its whole process tree.
            proc.communicate(timeout=self.policy.cleanup_timeout)

    def probe(self, timeout=None):
        value = self.command_json(["runtimes", "status", self.c.alias, "--json"], timeout=timeout)
        if value.get("alias_missing") is True:
            return value
        # Incomplete/mismatched alias metadata never authorizes adoption or a new connect.
        for name, expected in (("profile_name", self.c.profile), ("profile_dir", str(self.c.profile_dir))):
            actual = value.get(name)
            if actual is None:
                raise LifecycleError("incomplete_runtime_status")
            if canonical(actual) != canonical(expected) if name == "profile_dir" else actual != expected:
                raise OwnershipError("runtime_alias_conflict")
        return value

    def verified_ready(self, value, daemons, frontends):
        if len(daemons) != 1:
            return False
        daemon = daemons[0]
        meta = value.get("process") or {}
        # PID must be independently observed with a full command/profile/exe/user identity.
        if meta.get("pid") != daemon.pid or not daemon.live():
            return False
        try:
            recorded_start = datetime.fromisoformat(meta["started_at"].replace("Z", "+00:00")).timestamp()
        except (KeyError, ValueError, TypeError) as exc:
            raise LifecycleError("runtime_start_identity_missing") from exc
        # The official CLI records start time rounded to whole seconds.
        if abs(recorded_start - daemon.created) > 1.5:
            raise OwnershipError("runtime_start_identity_conflict")
        if meta.get("profile_name") != self.c.profile or canonical(meta.get("profile_dir", ".")) != canonical(
            self.c.profile_dir
        ):
            raise OwnershipError("runtime_process_scope_conflict")
        child_counts = {}
        attached = {daemon.pid: daemon}
        remaining = list(frontends)
        while remaining:
            linked = [
                p
                for p in remaining
                if p.parent_pid in attached
                and p.parent_created == attached[p.parent_pid].created
                and p.created >= attached[p.parent_pid].created
                and p.live()
            ]
            if not linked:
                return False
            attached.update({p.pid: p for p in linked})
            remaining = [p for p in remaining if p not in linked]
        for child in frontends:
            child_counts[child.parent_pid] = child_counts.get(child.parent_pid, 0) + 1
        if not frontends or any(count > 1 for count in child_counts.values()):
            return False
        return all(value.get(field) is True for field in ("process_running", "ready", "healthy"))

    def terminate(self, identity):
        if not identity.live():
            return
        p = psutil.Process(identity.pid)
        # Fresh identity and role evidence immediately before the destructive action.
        if identity.role == "daemon" and not self._daemon(p):
            raise OwnershipError("daemon_ownership_changed")
        if identity.role == "frontend" and "serve" not in p.cmdline():
            raise OwnershipError("frontend_ownership_changed")
        if not identity.live():
            return
        try:
            if p.status() == psutil.STATUS_STOPPED:
                # POSIX SIGTERM is deferred while stopped. A fenced frozen producer
                # must be killed without resuming its ability to spawn children.
                p.kill()
            else:
                p.terminate()
            p.wait(self.policy.cleanup_timeout)
        except psutil.NoSuchProcess:
            return
        except psutil.TimeoutExpired as exc:
            if not identity.live():
                return  # An orphaned POSIX zombie is dead, even if its adopter has not reaped it.
            raise OwnershipError("owned_process_did_not_stop") from exc

    def reconcile(self):
        self.scan()  # Even failed status/empty registry cannot hide an exact scoped daemon.
        # Freeze only proven connector producers before enumerating their children.
        # Otherwise a daemon can spawn an MCP between enumeration and termination,
        # leaving an orphan whose parent creation identity was never observed.
        frozen = []
        deadline = time.monotonic() + self.policy.cleanup_timeout
        try:
            while True:
                candidates = [p for p in self.known if p not in frozen and p.live()]
                if not candidates:
                    break
                for identity in candidates:
                    if time.monotonic() >= deadline:
                        raise OwnershipError("producer_quiesce_timeout")
                    process = psutil.Process(identity.pid)
                    if identity.role == "daemon" and not self._daemon(process):
                        raise OwnershipError("daemon_ownership_changed")
                    if identity.role == "frontend" and "serve" not in process.cmdline():
                        raise OwnershipError("frontend_ownership_changed")
                    if identity.live():
                        try:
                            process.suspend()
                            frozen.append(identity)
                            while identity.live() and process.status() != psutil.STATUS_STOPPED:
                                if time.monotonic() >= deadline:
                                    raise OwnershipError("producer_quiesce_timeout")
                                time.sleep(0.01)
                        except psutil.NoSuchProcess:
                            continue
                self.scan()
            # Native workers, durable supervisors and unrelated hosts were never frozen.
            for role in ("daemon", "frontend"):
                for identity in frozen:
                    if identity.role == role:
                        self.terminate(identity)
        finally:
            # A refused cleanup must not leave preserved/ambiguous owners suspended.
            resume_errors = []
            for identity in frozen:
                try:
                    if identity.live():
                        psutil.Process(identity.pid).resume()
                except psutil.NoSuchProcess:
                    pass
                except (psutil.Error, OwnershipError):
                    resume_errors.append(identity.pid)
            if resume_errors:
                raise OwnershipError("preserved_process_resume_unconfirmed")
        self.scan()
        if any(p.live() for p in self.known):
            raise OwnershipError("cleanup_incomplete")
        self.known = []
        self.save()

    def ready(self):
        deadline = time.monotonic() + self.policy.ready_timeout
        while time.monotonic() < deadline:
            self.check_stop()
            daemons, frontends = self.scan()
            if len(daemons) > 1:
                raise LifecycleError("duplicate_scoped_daemons")
            try:
                value = self.probe(min(self.policy.command_timeout, max(0.01, deadline - time.monotonic())))
            except LifecycleError as exc:
                if str(exc) == "command_timeout" and time.monotonic() >= deadline:
                    raise LifecycleError("readiness_timeout") from exc
                raise
            if self.verified_ready(value, daemons, frontends):
                return daemons[0]
            self.note("starting", reason="waiting_for_healthy_mcp")
            self.pause(min(self.policy.poll, max(0, deadline - time.monotonic())))
        raise LifecycleError("readiness_timeout")

    def connect(self):
        profile = read(self.c.profile_path)
        control = profile.get("control_plane", {})
        tunnel_id = control.get("tunnel_id", "")
        if not re.fullmatch(r"tunnel_[a-f0-9]+", tunnel_id):
            raise LifecycleError("invalid_existing_tunnel_identity")
        if control.get("api_key") != "env:CONTROL_PLANE_API_KEY":
            raise LifecycleError("runtime_key_reference_required")
        if not self.c.engine.is_file() or not self.c.tunnel_client.is_file():
            raise LifecycleError("runtime_executable_missing")
        self.attempt = {"started_at": utc(), "supervisor": asdict(self.owner)}
        self.save()  # Durable intent precedes the first spawn-capable command.
        self.note("spawning")
        self.command_json(
            [
                "runtimes",
                "connect",
                "--json",
                "--alias",
                self.c.alias,
                "--profile",
                self.c.profile,
                "--profile-dir",
                str(self.c.profile_dir),
                "--tunnel-id",
                tunnel_id,
                "--mcp-command",
                f'"{self.c.engine.as_posix()}" serve',
                "--runtime-api-key",
                "env:CONTROL_PLANE_API_KEY",
            ],
            observe=True,
        )
        return self.ready()

    def ensure_ready(self):
        daemons, frontends = self.scan()
        value = self.probe()
        if value.get("alias_missing") is True:
            # No new remote identity is created: connect still requires the user's
            # existing validated tunnel ID. Reconcile OS owners before registration.
            self.reconcile()
            return self.connect()
        if self.verified_ready(value, daemons, frontends):
            return daemons[0]
        if len(daemons) == 1:
            # Adopt and poll a starting owner instead of spawning another one.
            return self.ready()
        self.reconcile()
        return self.connect()

    def supervise(self):
        failures = 0
        while True:
            try:
                self.check_stop()
                daemon = self.ensure_ready()
                healthy_since = time.monotonic()
                while True:
                    self.note("ready", ready=True, healthy=True, daemon=daemon)
                    self.pause(self.policy.health_interval)
                    daemons, frontends = self.scan()
                    value = self.probe()
                    if not self.verified_ready(value, daemons, frontends):
                        raise LifecycleError("runtime_unhealthy")
                    daemon = daemons[0]
                    if time.monotonic() - healthy_since >= 300:
                        failures = 0
            except StopRequested:
                self.note("stopping")
                self.reconcile()
                return self.note("stopped")
            except OwnershipError as exc:
                self.note("unknown", reason=str(exc))
                raise  # Preserve ambiguous processes; never start another attempt.
            except Exception as exc:
                reason = str(exc) if isinstance(exc, LifecycleError) else "supervisor_error"
                self.note("unhealthy", reason=reason)
                try:
                    self.reconcile()
                except Exception:
                    self.note("unknown", reason="reconciliation_failed")
                    raise
                if reason == "authentication_required" or failures >= len(self.policy.retries):
                    self.note("failed", reason=reason)
                    raise LifecycleError(reason) from None
                delay = self.policy.retries[failures]
                failures += 1
                try:
                    self.pause(delay)
                except StopRequested:
                    return self.note("stopped")


def allow_start(config_path):
    c = Connection.load(config_path)
    write_json(c.cloud_root / "intent.json", {"enabled": True, "stop_requested": False, "updated_at": utc()})
    return {"state": "allowed", "scope": c.scope}


def run(config_path):
    c = Connection.load(config_path)
    try:
        with file_lock(c.lock, timeout=0):
            controller = Controller(c)
            return controller.supervise()
    except BusyError:
        return {"state": "already_supervised", "scope": c.scope}


def stop_legacy_wrappers(c):
    if os.name != "nt":
        return
    expected_exe = canonical(
        Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    script = canonical(c.cloud_root / "Run-ChatGPT-Tunnel.ps1")
    ancestors = {p.pid for p in psutil.Process().parents()} | {os.getpid()}
    for p in psutil.process_iter(["name"]):
        if p.info["name"].lower() != "powershell.exe" or p.pid in ancestors:
            continue
        try:
            if p.username() != psutil.Process().username() or canonical(p.exe()) != expected_exe:
                continue
            argv = p.cmdline()
            # Windows PowerShell options are case-insensitive; path values are not lowercased here.
            flag = next((a for a in argv if a.lower() == "-file"), "-File")
            target = option(argv, flag)
            if target and canonical(target) == script:
                owner = Identity.capture(p, "legacy_wrapper")
                if owner.live():
                    p.terminate()
                    p.wait(8)
        except psutil.NoSuchProcess:
            continue
        except (psutil.AccessDenied, psutil.TimeoutExpired) as exc:
            raise OwnershipError("legacy_wrapper_stop_unconfirmed") from exc


def stop(config_path, *, disable=True):
    c = Connection.load(config_path)
    intent = c.intent()
    intent.update(stop_requested=True, updated_at=utc())
    if disable:
        intent["enabled"] = False
    write_json(c.cloud_root / "intent.json", intent)
    try:
        with file_lock(c.lock, timeout=45):
            # New owners released this lock cooperatively. Legacy wrappers have no
            # lock/stop protocol; stop only their freshly fenced PowerShell process.
            stop_legacy_wrappers(c)
            controller = Controller(c)
            controller.note("stopping")
            controller.reconcile()
            return controller.note("stopped")
    except BusyError as exc:
        raise OwnershipError("supervisor_stop_unconfirmed") from exc


def status(config_path):
    c = Connection.load(config_path)
    value = read(
        c.cloud_root / "supervisor-state.json", {"state": "absent", "ready": False, "healthy": False}
    )
    owner = value.get("supervisor")
    daemon = value.get("daemon")
    if value.get("ready") and (
        time.time() > value.get("valid_until", 0)
        or not owner
        or not Identity(**owner).live()
        or not daemon
        or not Identity(**daemon).live()
    ):
        return {**value, "state": "stale", "ready": False, "healthy": False}
    return value
