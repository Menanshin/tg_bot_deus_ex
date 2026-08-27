"""Состояние: персистентность, конкурентная запись, лимиты."""

import json
import logging
import threading


def test_state_survives_restart(mod):
    mod.whitelist_gpt4.add(-100500)
    mod.username_to_id["@chan"] = -100500
    mod.save_state()

    mod.whitelist_gpt4.clear()
    mod.username_to_id.clear()
    mod.load_state()

    assert mod.whitelist_gpt4 == {-100500}
    assert mod.username_to_id == {"@chan": -100500}


def test_missing_state_file_is_not_fatal(mod):
    mod.STATE_FILE.unlink(missing_ok=True)
    mod.load_state()  # не должно бросать


def test_corrupted_state_file_is_not_fatal(mod):
    mod.STATE_FILE.write_text("{это не json", encoding="utf-8")
    mod.load_state()


def test_concurrent_writes_keep_file_valid(mod, caplog):
    """Регрессия: общий .tmp на все потоки давал FileNotFoundError на os.replace."""

    def hammer(n):
        for _ in range(30):
            mod.record_post(-100 - n, f"@ch{n}", "текст", "коммент", "gpt-4o-mini")

    with caplog.at_level(logging.ERROR):
        threads = [threading.Thread(target=hammer, args=(n,)) for n in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert caplog.records == []
    data = json.loads(mod.STATE_FILE.read_text(encoding="utf-8"))
    assert sum(v["count"] for v in data["channel_stats"].values()) == 480
    assert list(mod.STATE_DIR.glob("*.tmp")) == []


def test_post_log_is_bounded(mod):
    assert mod.post_log.maxlen == mod.POST_LOG_LIMIT
    for i in range(mod.POST_LOG_LIMIT + 50):
        mod.post_log.append({"i": i})
    assert len(mod.post_log) == mod.POST_LOG_LIMIT
