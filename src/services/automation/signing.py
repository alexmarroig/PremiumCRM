import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from itertools import cycle
from typing import Optional

from core.config import get_settings
from db.models import AutomationDestination


def build_signature_base_string(timestamp: str, event_id: str, tenant_id: str, body: bytes) -> str:
    body_str = body.decode("utf-8")
    return f"{timestamp}.{event_id}.{tenant_id}.{body_str}"


def _signature_payload(timestamp: str, event_id: str, tenant_id: str, body: bytes) -> bytes:
    return build_signature_base_string(timestamp, event_id, tenant_id, body).encode("utf-8")


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


def _encryption_key_bytes() -> bytes:
    settings = get_settings()
    key = os.getenv("AUTOMATION_SECRET_ENCRYPTION_KEY") or settings.secret_key
    return hashlib.sha256(key.encode("utf-8")).digest()


def encrypt_secret(secret: str) -> str:
    if not secret:
        return ""
    key_stream = cycle(_encryption_key_bytes())
    encrypted = bytes([char ^ next(key_stream) for char in secret.encode("utf-8")])
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def decrypt_secret(encrypted_secret: str) -> Optional[str]:
    if not encrypted_secret:
        return None
    try:
        data = base64.urlsafe_b64decode(encrypted_secret.encode("utf-8"))
    except Exception:
        return None
    key_stream = cycle(_encryption_key_bytes())
    decrypted = bytes([char ^ next(key_stream) for char in data])
    return decrypted.decode("utf-8")


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


def resolve_destination_secret(destination: AutomationDestination) -> Optional[str]:
    env_secret = resolve_secret(destination.secret_env_key)
    if env_secret:
        return env_secret
    return decrypt_secret(destination.secret_encrypted or "")
