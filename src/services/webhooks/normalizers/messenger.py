def normalize(payload: dict) -> dict:
    return {
        "channel_type": "messenger",
        "channel_message_id": payload.get("mid"),
        "handle": payload.get("sender", {}).get("id"),
        "name": payload.get("sender", {}).get("name"),
        "avatar_url": payload.get("sender", {}).get("avatar"),
        "body": payload.get("text"),
        "timestamp": payload.get("timestamp"),
    }
