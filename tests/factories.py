"""Конструкторы апдейтов Telegram для тестов."""

CHANNEL_ID = -1001234567890
DISCUSSION_ID = -1009876543210


def channel_post(text="Пост в канале.", update_id=1):
    return {
        "update_id": update_id,
        "channel_post": {
            "message_id": 10,
            "date": 1700000000,
            "chat": {"id": CHANNEL_ID, "type": "channel", "username": "TestChan"},
            "text": text,
        },
    }


def discussion_forward(text="Пост в канале.", update_id=2, automatic=True):
    return {
        "update_id": update_id,
        "message": {
            "message_id": 77,
            "date": 1700000001,
            "chat": {"id": DISCUSSION_ID, "type": "supergroup", "title": "Chat"},
            "from": {"id": 777000, "is_bot": False, "first_name": "Telegram"},
            "is_automatic_forward": automatic,
            "forward_from_chat": {
                "id": CHANNEL_ID,
                "type": "channel",
                "username": "TestChan",
            },
            "forward_from_message_id": 10,
            "text": text,
        },
    }


def command(text, user_id, update_id=99):
    return {
        "update_id": update_id,
        "message": {
            "message_id": 5,
            "date": 1700000002,
            "chat": {"id": user_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "U"},
            "text": text,
            "entities": [
                {"offset": 0, "type": "bot_command", "length": len(text.split()[0])}
            ],
        },
    }
