"""HMAC privacy helpers with a per-install secret."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from pathlib import Path

from .config import ROOT

SECRET_PATH = ROOT / "data" / ".shg_salt"
INSECURE_DEFAULT = "demo-salt-change"


def get_salt() -> str:
    """Load an environment secret or create a private per-install secret."""
    environment = os.environ.get("SHG_SALT")
    if environment:
        if environment == INSECURE_DEFAULT:
            raise RuntimeError("Refusing insecure default SHG_SALT; set a strong secret")
        return environment
    SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SECRET_PATH.exists():
        SECRET_PATH.write_text(secrets.token_urlsafe(48))
        SECRET_PATH.chmod(0o600)
    return SECRET_PATH.read_text().strip()


def hash_identifier(value: object, salt: str | None = None) -> str:
    secret = (salt or get_salt()).encode()
    clean = re.sub(r"\s+", "", str(value).strip().lower()).encode()
    return hmac.new(secret, clean, hashlib.sha256).hexdigest()


def alias(value: str, prefix: str = "External") -> str:
    return f"{prefix}-{value[:4].upper()}"


def scrub(text: str) -> str:
    return re.sub(r"\b\d{10,16}\b", "[REDACTED]", str(text))
