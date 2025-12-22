from datetime import timedelta

from core.security import create_token, decode_token, get_password_hash, verify_password


def test_password_hash_roundtrip():
    password = "secret123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)


def test_token_create_and_decode():
    token = create_token("user123", timedelta(minutes=5), "access")
    sub = decode_token(token, "access")
    assert sub == "user123"
