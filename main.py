import datetime
import json
import logging
import os

from dotenv import load_dotenv
from flask import Flask, request
from openai import OpenAI
from telegram import Bot, Update  # BotCommand, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Dispatcher,
    Filters,
    MessageHandler,
)

# === Загрузка переменных окружения ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# === Инициализация ===
bot = Bot(token=TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
dispatcher = Dispatcher(bot, None, workers=2, use_context=True)

post_log = []
channel_stats = {}
whitelist_gpt4 = set()
username_to_id = {}

# === Flask-приложение ===
app = Flask(__name__)


# === Вспомогательные функции ===
def save_whitelist():
    try:
        with open("whitelist.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "gpt4_whitelist": list(whitelist_gpt4),
                    "username_map": username_to_id,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        logging.error(f"Ошибка при сохранении whitelist: {e}")


def generate_ai_comment(post_text, use_gpt4=False):
    model = "gpt-4" if use_gpt4 else "gpt-3.5-turbo"
    messages = [
        {
            "role": "system",
            "content": (
                "Ты ИИ-комментатор. Комментируй посты точно и глубоко. "
                "Уточняй ошибки, предлагай улучшения, расшифровывай медиа по описанию. "
                "Заверши каждый комментарий строкой: "
                "'Есть вопросы о моей работе? Обратитесь к моему создателю @menanshin'"
            ),
        },
        {"role": "user", "content": post_text},
    ]
    try:
        response = client.chat.completions.create(model=model, messages=messages)
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Ошибка генерации комментария ({model}): {e}")
        return "(Комментарий не сгенерирован)"


# === Обработчики ===
def handle_post(update: Update, context: CallbackContext):
    if update.message.chat.type != "channel":
        return

    text = update.message.text
    chat = update.message.chat
    chat_id = chat.id
    username = chat.username

    if username:
        username_to_id[f"@{username.lower()}"] = chat_id

    use_gpt4 = chat_id in whitelist_gpt4
    comment = generate_ai_comment(text, use_gpt4=use_gpt4)
    bot.send_message(chat_id=chat_id, text=comment)

    channel_stats.setdefault(
        chat_id, {"count": 0, "model": "gpt-4" if use_gpt4 else "gpt-3.5-turbo"}
    )
    channel_stats[chat_id]["count"] += 1

    post_log.append(
        {
            "timestamp": str(datetime.datetime.now()),
            "chat_id": chat_id,
            "username": username,
            "original": text,
            "comment": comment,
            "model": channel_stats[chat_id]["model"],
        }
    )


def report(update: Update, context: CallbackContext):
    send_weekly_report_for_chat(update.message.chat.id, context)


def send_weekly_report_for_chat(chat_id, context):
    relevant = [p for p in post_log if p["chat_id"] == chat_id]
    if not relevant:
        return
    filename = (
        f"weekly_report_{chat_id}_{datetime.datetime.now().strftime('%Y%m%d')}.json"
    )
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(relevant, f, ensure_ascii=False, indent=2)
    context.bot.send_document(
        chat_id=chat_id, document=open(filename, "rb"), filename=filename
    )


def status(update: Update, context: CallbackContext):
    if update.message.from_user.id != OWNER_ID:
        return
    if not channel_stats:
        update.message.reply_text("Нет данных по активности.")
        return
    id_to_username = {v: k for k, v in username_to_id.items()}
    text = "Статистика по каналам:\n"
    for cid, data in channel_stats.items():
        username = id_to_username.get(cid, f"(ID {cid})")
        text += f"\n{username}: {data['count']} комментариев, модель: {data['model']}"
    update.message.reply_text(text)


def allow(update: Update, context: CallbackContext):
    if update.message.from_user.id != OWNER_ID:
        return
    if not context.args:
        update.message.reply_text("Укажи username или chat_id")
        return
    target = context.args[0]
    if target.startswith("@"):  # username
        chat_id = username_to_id.get(target.lower())
        if chat_id:
            whitelist_gpt4.add(chat_id)
            save_whitelist()
            update.message.reply_text(f"Канал {target} добавлен в whitelist")
    else:
        try:
            chat_id = int(target)
            whitelist_gpt4.add(chat_id)
            save_whitelist()
            update.message.reply_text(f"Канал {chat_id} добавлен в whitelist")
        except Exception:
            update.message.reply_text("Некорректный ID")


def remove(update: Update, context: CallbackContext):
    if update.message.from_user.id != OWNER_ID:
        return
    if not context.args:
        update.message.reply_text("Укажи username или chat_id")
        return
    target = context.args[0]
    try:
        chat_id = (
            int(target)
            if not target.startswith("@")
            else username_to_id.get(target.lower())
        )
        if chat_id and chat_id in whitelist_gpt4:
            whitelist_gpt4.remove(chat_id)
            save_whitelist()
            update.message.reply_text(f"Канал {target} удалён из whitelist")
        else:
            update.message.reply_text("Канал не найден или не в whitelist")
    except Exception:
        update.message.reply_text("Ошибка")


def dump_whitelist(update: Update, context: CallbackContext):
    if update.message.from_user.id == OWNER_ID:
        try:
            update.message.reply_document(document=open("whitelist.json", "rb"))
        except Exception:
            update.message.reply_text("Файл не найден.")


# === Регистрируем обработчики ===
dispatcher.add_handler(CommandHandler("report", report))
dispatcher.add_handler(CommandHandler("status", status))
dispatcher.add_handler(CommandHandler("allow", allow))
dispatcher.add_handler(CommandHandler("remove", remove))
dispatcher.add_handler(CommandHandler("dump_whitelist", dump_whitelist))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_post))


# === Flask routes ===
@app.route("/", methods=["GET"])
def index():
    return "\u2705 Бот работает."


@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"


# === Запуск ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=5000)
