from datetime import datetime, timedelta, timezone

from services.automation.signing import (
    build_signature_base_string,
    decrypt_secret,
    encrypt_secret,
    is_timestamp_within_window,
    resolve_destination_secret,
    serialize_callback_body,
    sign_payload,
    verify_signature,
)


def test_signing_roundtrip(monkeypatch):
    monkeypatch.setenv("AUTOMATION_REPLAY_WINDOW_SECONDS", "300")
    secret = "super-secret"
    body = b'{"hello":"world"}'
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    signature = sign_payload(secret, timestamp, "event-1", "tenant-1", body)
    assert verify_signature(secret, timestamp, "event-1", "tenant-1", body, signature)


def test_replay_window_rejects_old_timestamp(monkeypatch):
    monkeypatch.setenv("AUTOMATION_REPLAY_WINDOW_SECONDS", "60")
    stale = datetime.now(timezone.utc) - timedelta(seconds=120)
    assert not is_timestamp_within_window(str(int(stale.timestamp())))


def test_secret_encryption_roundtrip(monkeypatch):
    monkeypatch.setenv("AUTOMATION_SECRET_ENCRYPTION_KEY", "test-key")
    secret = "callback-secret"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret


def test_resolve_destination_secret_uses_encrypted_when_env_missing(monkeypatch):
    monkeypatch.delenv("AUTOMATION_DESTINATION_SECRET_FOO", raising=False)
    monkeypatch.setenv("AUTOMATION_SECRET_ENCRYPTION_KEY", "test-key")
    encrypted = encrypt_secret("stored-secret")

    destination = type("Destination", (), {
        "secret_env_key": "AUTOMATION_DESTINATION_SECRET_FOO",
        "secret_encrypted": encrypted,
    })

    assert resolve_destination_secret(destination) == "stored-secret"


def test_signature_base_string_spec_example():
    body = {
        "tenant_id": "tenant_abc",
        "action": "create_task",
        "payload": {"title": "Ligar para cliente"},
    }
    body_json = serialize_callback_body(body)
    base_string = build_signature_base_string(
        "1700000000",
        "evt_123",
        "tenant_abc",
        body_json.encode("utf-8"),
    )
    assert (
        base_string
        == '1700000000.evt_123.tenant_abc.{"tenant_id":"tenant_abc","action":"create_task","payload":{"title":"Ligar para cliente"}}'
    )
    assert (
        sign_payload("super-secret", "1700000000", "evt_123", "tenant_abc", body_json.encode("utf-8"))
        == "098db21286883fa0f8368d83f132ca655f2fd8bb4d4841d10c1b06604e61cc37"
    )
