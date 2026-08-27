"""Обработка постов и команд."""

import json

import pytest
from telegram import Message, Update

from tests.factories import (
    CHANNEL_ID,
    DISCUSSION_ID,
    channel_post,
    command,
    discussion_forward,
)


def process(mod, payload):
    mod.dispatcher.process_update(Update.de_json(payload, mod.bot))


def test_channel_post_does_not_crash(mod):
    """Регрессия: раньше здесь падало AttributeError на update.message == None."""
    process(mod, channel_post())
    assert mod.username_to_id == {"@testchan": CHANNEL_ID}


def test_comment_goes_to_discussion_as_reply(mod):
    process(mod, discussion_forward())
    assert mod.sent == [(DISCUSSION_ID, "Комментарий ИИ.", 77)]
    assert mod.channel_stats[CHANNEL_ID]["count"] == 1


def test_manual_forward_ignored(mod):
    """Комментируем только автопересылки канала, не пересылки людей."""
    process(mod, discussion_forward(automatic=False))
    assert mod.sent == []


def test_caption_only_post_is_commented(mod):
    payload = discussion_forward()
    del payload["message"]["text"]
    payload["message"]["photo"] = [
        {"file_id": "x", "file_unique_id": "y", "width": 1, "height": 1}
    ]
    payload["message"]["caption"] = "Подпись к картинке"
    process(mod, payload)
    assert len(mod.sent) == 1


def test_whitelist_selects_premium_model(mod):
    mod.whitelist_gpt4.add(CHANNEL_ID)
    process(mod, discussion_forward())
    assert mod.channel_stats[CHANNEL_ID]["model"] == mod.MODEL_PREMIUM


def test_failed_generation_sends_nothing(mod, monkeypatch):
    monkeypatch.setattr(mod, "generate_ai_comment", lambda t, use_gpt4=False: None)
    process(mod, discussion_forward())
    assert mod.sent == []
    assert mod.post_log == mod.post_log.__class__(maxlen=mod.POST_LOG_LIMIT)


@pytest.fixture
def replies(monkeypatch):
    out = []
    monkeypatch.setattr(
        Message, "reply_text", lambda self, text, *a, **k: out.append(text)
    )
    return out


@pytest.mark.parametrize("cmd", ["/status", "/report", "/allow 1", "/remove 1"])
def test_commands_ignore_strangers(mod, replies, cmd):
    process(mod, command(cmd, user_id=5))
    assert replies == []


def test_allow_by_username(mod, replies):
    process(mod, channel_post())
    process(mod, command("/allow @testchan", user_id=42))
    assert mod.whitelist_gpt4 == {CHANNEL_ID}
    assert "whitelist" in replies[-1]


def test_allow_by_id_and_remove(mod, replies):
    process(mod, command("/allow -100500", user_id=42))
    assert mod.whitelist_gpt4 == {-100500}
    process(mod, command("/remove -100500", user_id=42))
    assert mod.whitelist_gpt4 == set()


def test_allow_garbage_answers(mod, replies):
    process(mod, command("/allow не_число", user_id=42))
    assert mod.whitelist_gpt4 == set()
    assert replies, "бот обязан ответить, а не молчать"


def test_remove_unknown_channel(mod, replies):
    process(mod, command("/remove @nope", user_id=42))
    assert "не найден" in replies[-1]


def test_status_reports_counts(mod, replies):
    process(mod, discussion_forward())
    process(mod, command("/status", user_id=42))
    assert "@testchan" in replies[-1] and "1 комментариев" in replies[-1]


def test_report_sends_document(mod, replies, monkeypatch):
    docs = []
    monkeypatch.setattr(
        mod.bot,
        "send_document",
        lambda chat_id, document, filename, **k: docs.append(
            (filename, json.loads(document.getvalue()))
        ),
    )
    process(mod, discussion_forward())
    process(mod, command("/report", user_id=42))
    assert len(docs) == 1
    assert docs[0][1][0]["chat_id"] == CHANNEL_ID
