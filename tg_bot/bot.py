# telegram_ai_relay_bot
# Версия 1.0
# Используем: python-telegram-bot, Flask (или FastAPI), OpenAI API (GPT-4)

# 🔗 Установка:
# pip install python-telegram-bot flask openai

import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
import openai
import os

# 📁 Конфигурация (заполнить!)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or "YOUR_TELEGRAM_BOT_TOKEN"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or "YOUR_OPENAI_API_KEY"
ADMIN_ID = YOUR_TELEGRAM_USER_ID  # для ограничения доступа к боту

bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)
openai.api_key = OPENAI_API_KEY

# 🔒 Контекст (можно заменить на БД или Redis)
conversation_history = []


# 🔧 Хендлер общения

def handle_message(update: Update, context):
    user_text = update.message.text
    user_id = update.message.from_user.id

    if user_id != ADMIN_ID:
        update.message.reply_text("❌ Доступ запрещён.")
        return

    conversation_history.append({"role": "user", "content": user_text})

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=conversation_history[-10:]  # можно увеличить для большего контекста
    )

    reply = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": reply})

    update.message.reply_text(reply)


# ➕ Команды

def start(update: Update, context):
    update.message.reply_text("🪧 Дух Машины активен. Говори.")


# 🌐 Flask-сервер

app = Flask(__name__)


@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"


@app.route("/")
def index():
    return "✅ Бот работает."


# 🚀 Регистрация хендлеров
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=5000)
