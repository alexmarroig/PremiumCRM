from services.webhooks.normalizers import whatsapp, instagram, messenger, email


def test_whatsapp_normalize():
    payload = {"id": "1", "from": "123", "message": "hi", "timestamp": "now"}
    result = whatsapp.normalize(payload)
    assert result["channel_type"] == "whatsapp"
    assert result["handle"] == "123"


def test_instagram_normalize():
    payload = {"message_id": "2", "user": {"username": "iguser"}, "text": "hello"}
    result = instagram.normalize(payload)
    assert result["channel_type"] == "instagram"
    assert result["handle"] == "iguser"


def test_messenger_normalize():
    payload = {"mid": "3", "sender": {"id": "abc"}, "text": "hello"}
    result = messenger.normalize(payload)
    assert result["channel_type"] == "messenger"
    assert result["handle"] == "abc"


def test_email_normalize():
    payload = {"message_id": "4", "from": "a@example.com", "body": "hello"}
    result = email.normalize(payload)
    assert result["channel_type"] == "email"
    assert result["handle"] == "a@example.com"
