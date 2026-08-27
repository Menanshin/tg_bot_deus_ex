"""Чистые функции: нарезка сообщений, разбор целей команд."""

import pytest


def test_short_text_is_one_chunk(mod):
    assert mod.split_message("короткий") == ["короткий"]


def test_long_text_respects_telegram_limit(mod):
    text = ("абзац " * 900 + "\n") * 3
    chunks = mod.split_message(text)
    assert len(chunks) > 1
    assert all(len(c) <= 4096 for c in chunks)


def test_split_prefers_newlines(mod):
    text = "a" * 4000 + "\n" + "b" * 4000
    assert mod.split_message(text)[0] == "a" * 4000


def test_split_handles_text_without_newlines(mod):
    chunks = mod.split_message("x" * 10000)
    assert [len(c) for c in chunks] == [4096, 4096, 1808]


def test_split_never_loses_characters(mod):
    text = ("строка данных " * 700).strip()
    assert "".join(mod.split_message(text)).replace("\n", "") == text.replace("\n", "")


@pytest.mark.parametrize(
    "target,expected",
    [("-100500", -100500), ("@known", -1), ("@unknown", None), ("мусор", None)],
)
def test_resolve_target(mod, target, expected):
    mod.username_to_id["@known"] = -1
    assert mod._resolve_target(target) == expected


def test_username_lookup_is_case_insensitive(mod):
    mod.username_to_id["@known"] = -1
    assert mod._resolve_target("@KnOwN") == -1


def test_dedup_window_is_bounded(mod):
    for i in range(mod._seen_updates.maxlen + 10):
        mod._seen_before(i)
    assert len(mod._seen_updates) == mod._seen_updates.maxlen
    assert mod._seen_before(mod._seen_updates.maxlen + 9) is True
