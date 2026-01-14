from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.routers.auth import LoginRequest, RegisterRequest, login, register
from core.security import create_token, decode_token, get_password_hash, verify_password
from db.base import Base
from db.models import Notification, User


def test_password_hash_roundtrip():
    password = "secret123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)


def test_token_create_and_decode():
    token = create_token("user123", timedelta(minutes=5), "access")
    sub = decode_token(token, "access")
    assert sub == "user123"


def _in_memory_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine, tables=[User.__table__, Notification.__table__])
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, TestingSession


def test_register_creates_onboarding_notification():
    engine, TestingSession = _in_memory_db()
    try:
        with TestingSession() as db:  # type: Session
            payload = RegisterRequest(name="Ada", email="ada@example.com", password="secret123")
            register(payload, db)

            user = db.query(User).first()
            notifications = db.query(Notification).filter(Notification.user_id == user.id).all()

            assert len(notifications) == 1
            assert notifications[0].type == "onboarding"
            assert "Bem-vindo" in notifications[0].message
    finally:
        engine.dispose()


def test_login_only_creates_welcome_once():
    engine, TestingSession = _in_memory_db()
    try:
        with TestingSession() as db:  # type: Session
            user = User(
                name="Linus",
                email="linus@example.com",
                password_hash=get_password_hash("password"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            login(LoginRequest(email=user.email, password="password"), db)
            login(LoginRequest(email=user.email, password="password"), db)

            notifications = db.query(Notification).filter(Notification.user_id == user.id).all()
            assert len(notifications) == 1
            assert notifications[0].type == "onboarding"
    finally:
        engine.dispose()
