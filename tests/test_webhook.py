"""Вебхук: авторизация, скорость ответа, идемпотентность."""

import json
import time

import pytest

from tests.factories import discussion_forward


@pytest.fixture
def client(mod):
    return mod.app.test_client()


@pytest.fixture
def url(mod):
    return f"/{mod.TELEGRAM_TOKEN}"


HDRS = {"X-Telegram-Bot-Api-Secret-Token": "s3cret"}


def post(client, url, payload, headers=HDRS):
    return client.post(
        url, data=json.dumps(payload), content_type="application/json", headers=headers
    )


def wait_for(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_rejects_wrong_secret(client, url):
    assert post(client, url, discussion_forward(), headers={}).status_code == 403


def test_rejects_broken_json(client, url):
    r = client.post(url, data="не json", content_type="application/json", headers=HDRS)
    assert r.status_code == 400


def test_acks_before_generating(mod, client, url):
    """Telegram не должен ждать OpenAI — иначе ретраи и дубли комментариев."""
    mod.generate_ai_comment = lambda t, use_gpt4=False: (
        time.sleep(1.0) or "Комментарий ИИ."
    )
    start = time.perf_counter()
    assert post(client, url, discussion_forward()).status_code == 200
    assert time.perf_counter() - start < 0.5
    assert wait_for(lambda: mod.sent)


def test_duplicate_updates_processed_once(mod, client, url):
    payload = discussion_forward(update_id=555)
    for _ in range(3):
        assert post(client, url, payload).status_code == 200
    assert wait_for(lambda: mod.sent)
    time.sleep(0.3)
    assert len(mod.sent) == 1
