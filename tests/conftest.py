"""Общая подготовка: фейковое окружение и заглушки вместо сети."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session", autouse=True)
def _env(tmp_path_factory):
    os.environ["TELEGRAM_TOKEN"] = "123456:FAKE"
    os.environ["OPENAI_API_KEY"] = "sk-fake"
    os.environ["OWNER_ID"] = "42"
    os.environ["STATE_DIR"] = str(tmp_path_factory.mktemp("state"))
    os.environ["WEBHOOK_SECRET"] = "s3cret"

    import telegram

    # dispatcher.start() дёргает getMe — в тестах сети нет
    telegram.Bot.get_me = lambda self, *a, **k: telegram.User(
        id=111, first_name="TestBot", is_bot=True, username="testbot"
    )


@pytest.fixture(scope="session")
def app_module(_env):
    import main

    return main


@pytest.fixture
def mod(app_module, monkeypatch):
    """Чистое состояние на каждый тест, OpenAI и отправка замоканы."""
    sent = []
    monkeypatch.setattr(
        app_module, "generate_ai_comment", lambda t, use_gpt4=False: "Комментарий ИИ."
    )
    monkeypatch.setattr(
        app_module,
        "send_long",
        lambda bot_, chat_id, text, reply_to: sent.append((chat_id, text, reply_to)),
    )
    app_module.whitelist_gpt4.clear()
    app_module.username_to_id.clear()
    app_module.channel_stats.clear()
    app_module.post_log.clear()
    app_module._seen_updates.clear()
    app_module.sent = sent
    return app_module
