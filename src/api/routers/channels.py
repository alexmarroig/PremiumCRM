from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/channels", tags=["channels"])


class ChannelType(BaseModel):
    type: str
    icon_key: str


SUPPORTED_CHANNELS = [
    ChannelType(type="whatsapp", icon_key="whatsapp"),
    ChannelType(type="instagram", icon_key="instagram"),
    ChannelType(type="messenger", icon_key="messenger"),
    ChannelType(type="email", icon_key="email"),
    ChannelType(type="other", icon_key="other"),
]


@router.get("", response_model=list[ChannelType])
def list_channels():
    return SUPPORTED_CHANNELS
