def normalize(payload: dict) -> dict:
    return {
        "channel_type": "whatsapp",
        "channel_message_id": payload.get("id"),
        "handle": payload.get("from"),
        "name": payload.get("name"),
        "avatar_url": payload.get("avatar"),
        "body": payload.get("message"),
        "timestamp": payload.get("timestamp"),
    }
