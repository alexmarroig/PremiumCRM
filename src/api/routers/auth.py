from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from api.deps import create_access_refresh_tokens
from core.security import TokenError, create_token, decode_token, get_password_hash, verify_password
from core.config import get_settings
from db.models import Notification, User
from db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


WELCOME_MESSAGE = (
    "Bem-vindo ao Alfred CRM! Geramos seus tokens de acesso e refresh, e sua conta já está "
    "habilitada para receber webhooks, criar notificações automáticas e acompanhar conversas "
    "com o assistente."
)


def ensure_onboarding_notification(user: User, db: Session) -> None:
    existing = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.type == "onboarding")
        .first()
    )
    if existing:
        return
    db.add(
        Notification(
            user_id=user.id,
            type="onboarding",
            entity_type="system",
            entity_id=user.id,
            message=WELCOME_MESSAGE,
        )
    )
    db.commit()


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email taken")
    user = User(name=payload.name, email=payload.email, password_hash=get_password_hash(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    tokens = create_access_refresh_tokens(str(user.id))
    ensure_onboarding_notification(user, db)
    return TokenResponse(**tokens)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    tokens = create_access_refresh_tokens(str(user.id))
    ensure_onboarding_notification(user, db)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest):
    try:
        user_id = decode_token(payload.refresh_token, expected_type="refresh")
    except TokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return TokenResponse(**create_access_refresh_tokens(user_id))
