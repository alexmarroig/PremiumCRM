import base64
import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Optional

from core.config import get_settings


def _signature_payload(timestamp: str, event_id: str, tenant_id: str, body: bytes) -> bytes:
    return b".".join([timestamp.encode("utf-8"), event_id.encode("utf-8"), tenant_id.encode("utf-8"), body])


def sign_payload(secret: str, timestamp: str, event_id: str, tenant_id: str, body: bytes) -> str:
    payload = _signature_payload(timestamp, event_id, tenant_id, body)
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return digest


def verify_signature(secret: str, timestamp: str, event_id: str, tenant_id: str, body: bytes, signature: str) -> bool:
    expected = sign_payload(secret, timestamp, event_id, tenant_id, body)
    return hmac.compare_digest(expected, signature)


def is_timestamp_within_window(timestamp: str) -> bool:
    settings = get_settings()
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    now = int(datetime.now(timezone.utc).timestamp())
    return abs(now - ts) <= settings.automation_replay_window_seconds


def mask_secret(secret: str) -> str:
    if not secret:
        return "***"
    if len(secret) <= 4:
        return "*" * len(secret)
    return f"***{secret[-4:]}"


def resolve_secret(secret_env_key: str) -> Optional[str]:
    return os.getenv(secret_env_key)


def ensure_secret_env(secret_env_key: str, secret: str) -> None:
    os.environ[secret_env_key] = secret


def build_env_key(destination_id: str) -> str:
    return f"AUTOMATION_DESTINATION_SECRET_{destination_id.replace('-', '').upper()}"


def decode_signature_header(signature: str) -> str:
    if signature.startswith("sha256="):
        return signature.split("=", 1)[1]
    return signature


def encode_basic_auth(secret: str) -> str:
    token = base64.b64encode(secret.encode("utf-8")).decode("utf-8")
    return token
