"""Pinned official tunnel dependency; no runtime download or floating version."""

import hashlib
from pathlib import Path

VERSION = "0.0.15"
ARCHIVE_NAME = f"tunnel-client-v{VERSION}-windows-amd64.zip"
ARCHIVE_SHA256 = "3b53133a1e24d43f63088d843860cb1701a4c3ed6390de2e19f69089e43bddc1"
EXECUTABLE_SHA256 = "1946de55a038313a9b9b2458d05fe1719fa9cf1f20a94dd5f38fc26a98bfdd42"
ARCHIVE_URL = f"https://github.com/openai/tunnel-client/releases/download/v{VERSION}/{ARCHIVE_NAME}"


def bundled_client(bundle):
    base = Path(bundle).resolve()
    candidate = base / "tunnel-client" / f"v{VERSION}" / "tunnel-client.exe"
    if candidate.resolve() != candidate or not candidate.is_file():
        raise ValueError("The pinned official tunnel client is missing or redirected")
    with candidate.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != EXECUTABLE_SHA256:
        raise ValueError("The pinned official tunnel client failed integrity verification")
    return candidate
