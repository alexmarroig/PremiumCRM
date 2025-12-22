def normalize(payload: dict) -> dict:
    return {
        "channel_type": "email",
        "channel_message_id": payload.get("message_id"),
        "handle": payload.get("from"),
        "name": payload.get("from_name"),
        "avatar_url": None,
        "body": payload.get("body"),
        "timestamp": payload.get("sent_at"),
    }
