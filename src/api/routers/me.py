from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import User

router = APIRouter(tags=["me"])


class MeResponse(BaseModel):
    id: str
    name: str
    email: EmailStr


@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return MeResponse(id=str(current_user.id), name=current_user.name, email=current_user.email)
