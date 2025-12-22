from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import Contact, ContactSettings, User
from db.session import get_db

router = APIRouter(prefix="/contacts", tags=["contacts"])


class ContactCreate(BaseModel):
    name: str
    handle: str
    avatar_url: str | None = None
    tags: list[str] = []


class ContactUpdate(BaseModel):
    name: str | None = None
    avatar_url: str | None = None
    tags: list[str] | None = None


class ContactSettingsUpdate(BaseModel):
    negotiation_enabled: bool | None = None
    base_price_default: float | None = None
    custom_price: float | None = None
    vip: bool | None = None
    preferred_tone: str | None = None


@router.get("", response_model=list[dict])
def list_contacts(q: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Contact).filter(Contact.user_id == current_user.id)
    if q:
        query = query.filter(Contact.name.ilike(f"%{q}%"))
    contacts = query.order_by(Contact.created_at.desc()).all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "handle": c.handle,
            "avatar_url": c.avatar_url,
            "tags": c.tags,
        }
        for c in contacts
    ]


@router.post("", response_model=dict)
def create_contact(payload: ContactCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(Contact).filter(Contact.user_id == current_user.id, Contact.handle == payload.handle).first()
    if existing:
        raise HTTPException(status_code=400, detail="Handle already exists")
    contact = Contact(
        user_id=current_user.id,
        name=payload.name,
        handle=payload.handle,
        avatar_url=payload.avatar_url,
        tags=payload.tags,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    db.add(ContactSettings(contact_id=contact.id))
    db.commit()
    return {"id": str(contact.id), "name": contact.name, "handle": contact.handle}


@router.patch("/{contact_id}", response_model=dict)
def update_contact(contact_id: str, payload: ContactUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == current_user.id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return {"id": str(contact.id), "name": contact.name, "handle": contact.handle}


@router.patch("/{contact_id}/settings")
def update_contact_settings(contact_id: str, payload: ContactSettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == current_user.id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    settings = contact.settings or ContactSettings(contact_id=contact.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    db.add(settings)
    db.commit()
    return {"status": "ok"}
