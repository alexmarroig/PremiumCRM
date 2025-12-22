def normalize(payload: dict) -> dict:
    return {
        "channel_type": "instagram",
        "channel_message_id": payload.get("message_id"),
        "handle": payload.get("user", {}).get("username"),
        "name": payload.get("user", {}).get("name"),
        "avatar_url": payload.get("user", {}).get("avatar"),
        "body": payload.get("text"),
        "timestamp": payload.get("timestamp"),
    }
