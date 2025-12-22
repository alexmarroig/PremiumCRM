import uuid
from datetime import datetime, timezone

from core.security import get_password_hash
from db.session import SessionLocal
from db.models import User, Channel, Contact, ContactSettings, Conversation, Message


def main():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "demo@alfred.ai").first()
        if existing:
            print("Demo user already exists")
            return
        user = User(name="Demo User", email="demo@alfred.ai", password_hash=get_password_hash("password"))
        db.add(user)
        db.commit()
        db.refresh(user)

        channel = Channel(user_id=user.id, type="email")
        db.add(channel)
        db.commit()
        db.refresh(channel)

        contact = Contact(user_id=user.id, name="Prospect Paula", handle="paula@example.com", avatar_url=None, tags=["lead"])
        db.add(contact)
        db.commit()
        db.refresh(contact)
        db.add(ContactSettings(contact_id=contact.id, negotiation_enabled=True, base_price_default=120))
        db.commit()

        convo = Conversation(user_id=user.id, contact_id=contact.id, channel_id=channel.id, status="open")
        db.add(convo)
        db.commit()
        db.refresh(convo)

        msg = Message(
            conversation_id=convo.id,
            direction="inbound",
            body="Hi, can we discuss pricing and timeline?",
            raw_payload={"seed": True},
            ai_classification={"sentiment": "neutral", "urgency": "normal"},
        )
        db.add(msg)
        convo.last_message_at = datetime.now(timezone.utc)
        convo.unread_count = 1
        db.commit()
        print("Seeded demo user with inbox")
    finally:
        db.close()


if __name__ == "__main__":
    main()
