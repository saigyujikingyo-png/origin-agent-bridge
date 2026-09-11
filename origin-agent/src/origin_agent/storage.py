"""Local snapshots, atomic metadata and cross-process device locking."""

import contextlib
import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path


def json_bytes(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(json_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(9):
            try:
                os.replace(temp, path)
                break
            except PermissionError:
                # Windows readers/antivirus can briefly hold a non-delete-sharing handle.
                if attempt == 8:
                    raise
                time.sleep(min(0.01 * 2**attempt, 0.15))
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def valid_id(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{32}", value):
        raise ValueError("Invalid identifier")
    return value


class BusyError(RuntimeError):
    pass


@contextlib.contextmanager
def file_lock(path: Path, timeout: float = 10):
    """OS releases this lock on process death; no stale lockfile deletion races."""
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    if path.stat().st_size == 0:
        stream.write(b"0")
        stream.flush()
    deadline = time.monotonic() + timeout
    locked = False
    try:
        while not locked:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except OSError:
                if time.monotonic() >= deadline:
                    raise BusyError("Origin device is busy; retry using the same plan ID") from None
                time.sleep(0.05)
        yield
    finally:
        if locked:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_UN)
        stream.close()


def default_roots() -> list[Path]:
    roots = [Path.home() / name for name in ("Documents", "Desktop", "Downloads")]
    if os.name == "nt":
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            ) as key:
                for name in ("Personal", "Desktop", "{374DE290-123F-4565-9164-39C4925E467B}"):
                    try:
                        roots.append(Path(os.path.expandvars(winreg.QueryValueEx(key, name)[0])))
                    except OSError:
                        pass
        except OSError:
            pass
    return [path.resolve() for path in roots if path.is_dir()]


class Store:
    def __init__(self, root: Path | None = None, allowed_roots: list[Path] | None = None):
        # A home dot-directory avoids MSIX LocalAppData redirection and OneDrive sync.
        base = Path.home() / ".origin-agent"
        self.root = (root or Path(os.environ.get("ORIGIN_AGENT_HOME", str(base)))).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if allowed_roots is None:
            config = os.environ.get("ORIGIN_AGENT_DATA_ROOTS")
            allowed_roots = [Path(p) for p in json.loads(config)] if config else default_roots()
        self.allowed_roots = list(dict.fromkeys([p.resolve() for p in allowed_roots] + [self.root / "inbox"]))
        for name in ("inbox", "datasets", "plans", "jobs", "sessions"):
            (self.root / name).mkdir(exist_ok=True)

    def path(self, kind: str, identifier: str) -> Path:
        if kind not in ("datasets", "plans", "jobs", "sessions"):
            raise ValueError("Invalid store kind")
        return self.root / kind / valid_id(identifier)

    def input_path(self, path: str, *, data_only: bool = True) -> Path:
        source = Path(path).expanduser().resolve(strict=True)
        if not source.is_file() or not any(source.is_relative_to(root) for root in self.allowed_roots):
            raise ValueError(
                "Input must be a file inside a configured data directory or the OriginAgent inbox"
            )
        if data_only and source.suffix.lower() not in (".csv", ".tsv", ".xlsx"):
            raise ValueError("Supported data files: CSV, TSV, XLSX")
        return source
