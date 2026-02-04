from datetime import datetime, timedelta, timezone

from services.automation.signing import is_timestamp_within_window, sign_payload, verify_signature


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
