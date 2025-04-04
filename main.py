# telegram_public_commentary_bot v3.6 — polling edition

import logging
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import openai
import os
import json
import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

openai.api_key = OPENAI_API_KEY

post_log = []
channel_stats = {}
whitelist_gpt4 = set()
username_to_id = {}

def save_whitelist():
    try:
        with open("whitelist.json", "w", encoding="utf-8") as f:
            json.dump({"gpt4_whitelist": list(whitelist_gpt4), "username_map": username_to_id}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка при сохранении whitelist: {e}")

def generate_ai_comment(post_text, use_gpt4=False):
    model = "gpt-4" if use_gpt4 else "gpt-3.5-turbo"
    messages = [
        {"role": "system", "content": (
            "Ты ИИ-комментатор. Комментируй посты точно и глубоко. Уточняй ошибки, предлагай улучшения, расшифровывай медиа по описанию."
            "Заверши каждый комментарий строкой: 'Если у вас есть вопросы о моей работе, то обратитесь к моему создателю @menanshin'"
        )},
        {"role": "user", "content": post_text}
    ]
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"AI comment error: {e}")
        return "(Комментарий не сгенерирован)"

def handle_post(update: Update, context: CallbackContext):
    text = update.message.text
    chat = update.message.chat
    chat_id = chat.id
    username = chat.username

    if username:
        username_to_id[f"@{username.lower()}"] = chat_id

    use_gpt4 = chat_id in whitelist_gpt4
    comment = generate_ai_comment(text, use_gpt4=use_gpt4)
    update.message.reply_text(comment)

    channel_stats.setdefault(chat_id, {"count": 0, "model": "gpt-4" if use_gpt4 else "gpt-3.5-turbo"})
    channel_stats[chat_id]["count"] += 1

    post_log.append({
        "timestamp": str(datetime.datetime.now()),
        "chat_id": chat_id,
        "username": username,
        "original": text,
        "comment": comment,
        "model": channel_stats[chat_id]["model"]
    })

def send_weekly_report_for_chat(chat_id):
    relevant = [p for p in post_log if p["chat_id"] == chat_id]
    if not relevant:
        return
    filename = f"weekly_report_{chat_id}_{datetime.datetime.now().strftime('%Y%m%d')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(relevant, f, ensure_ascii=False, indent=2)
    bot.send_document(chat_id=chat_id, document=open(filename, "rb"), filename=filename,
                      caption="Ваш еженедельный отчёт. Вы можете отправить этот файл создателю бота (@menanshin) для анализа контента и рекомендаций.")

def report(update: Update, context: CallbackContext):
    send_weekly_report_for_chat(update.message.chat.id)

def status(update: Update, context: CallbackContext):
    if update.message.from_user.id != OWNER_ID:
        return
    if not channel_stats:
        update.message.reply_text("Нет данных по активности.")
        return
    text = "Статистика по каналам:\n"
    for cid, data in channel_stats.items():
        text += f"\nКанал {cid}: {data['count']} комментариев, модель: {data['model']}"
    update.message.reply_text(text)

def allow(update: Update, context: CallbackContext):
    if update.message.from_user.id != OWNER_ID:
        return
    if not context.args:
        update.message.reply_text("Укажи username или chat_id: /allow @channel_username или /allow 123456")
        return
    target = context.args[0]
    if target.startswith("@"):
        chat_id = username_to_id.get(target.lower())
        if chat_id:
            whitelist_gpt4.add(chat_id)
            save_whitelist()
            update.message.reply_text(f"Канал {target} ({chat_id}) добавлен в whitelist GPT-4")
        else:
            update.message.reply_text(f"Канал {target} не найден. Убедись, что бот был добавлен и активен в этом канале.")
    else:
        try:
            chat_id = int(target)
            whitelist_gpt4.add(chat_id)
            save_whitelist()
            update.message.reply_text(f"Канал {chat_id} добавлен в whitelist GPT-4")
        except:
            update.message.reply_text("Ошибка: некорректный ID")

def remove(update: Update, context: CallbackContext):
    if update.message.from_user.id != OWNER_ID:
        return
    if not context.args:
        update.message.reply_text("Укажи username или chat_id: /remove @channel_username или /remove 123456")
        return
    target = context.args[0]
    if target.startswith("@"):
        chat_id = username_to_id.get(target.lower())
        if chat_id and chat_id in whitelist_gpt4:
            whitelist_gpt4.remove(chat_id)
            save_whitelist()
            update.message.reply_text(f"Канал {target} удалён из whitelist GPT-4")
        else:
            update.message.reply_text(f"Канал {target} не найден в whitelist")
    else:
        try:
            chat_id = int(target)
            if chat_id in whitelist_gpt4:
                whitelist_gpt4.remove(chat_id)
                save_whitelist()
                update.message.reply_text(f"Канал {chat_id} удалён из whitelist GPT-4")
            else:
                update.message.reply_text("Этот канал не находится в whitelist")
        except:
            update.message.reply_text("Ошибка: некорректный ID")

def dump_whitelist(update: Update, context: CallbackContext):
    if update.message.from_user.id == OWNER_ID:
        try:
            update.message.reply_document(document=open("whitelist.json", "rb"), filename="whitelist.json")
        except:
            update.message.reply_text("Файл whitelist.json не найден.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("report", report))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("allow", allow))
    dp.add_handler(CommandHandler("remove", remove))
    dp.add_handler(CommandHandler("dump_whitelist", dump_whitelist))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_post))

    updater.start_polling()
    updater.idle()
