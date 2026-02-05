from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"], default="pbkdf2_sha256", deprecated="auto"
)


class TokenError(Exception):
    pass


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    # Let passlib choose the configured default scheme.
    # This avoids hardcoding optional algorithms that may not be installed
    # in every environment (e.g. bcrypt_sha256) and removes deprecated usage
    # of the `scheme` argument.
    return pwd_context.hash(password)


def create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    settings = get_settings()
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "exp": datetime.now(timezone.utc) + expires_delta,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def decode_token(token: str, expected_type: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != expected_type:
            raise TokenError("Invalid token type")
        return str(payload.get("sub"))
    except JWTError as exc:
        raise TokenError("Invalid token") from exc
