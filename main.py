import asyncio
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

from config import BOT_TOKEN, WEBAPP_URL
from ai import generate_prediction
from db import init_db, save, get_last

ASK = 1

menu = ReplyKeyboardMarkup([
    ["🔮 Получить предсказание"],
    [KeyboardButton("📱 Открыть приложение",
        web_app=WebAppInfo(url=WEBAPP_URL))]
], resize_keyboard=True)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = f"@{user.username}" if user.username else user.first_name

    text = f"""
✨ <b>Привет, {name}</b>

Я — твой проводник в мире Таро и звёзд 🌌

🔮 Предсказания на день  
🔢 Нумерология  
🌌 Натальная карта  

Выбери путь 👇
"""
    await update.message.reply_text(text, reply_markup=menu, parse_mode="HTML")

# предсказание
async def predict_start(update, context):
    await update.message.reply_text("💭 Что тебя волнует сегодня?")
    return ASK

async def predict_answer(update, context):
    user_input = update.message.text

    await update.message.chat.send_action("typing")

    history = await get_last(update.effective_user.id)
    hist_text = "\n".join([h[0] for h in history])

    result = await generate_prediction(user_input, hist_text)

    await update.message.reply_text(result, parse_mode="HTML", reply_markup=menu)

    await save(update.effective_user.id, user_input, result, "predict")

    return ConversationHandler.END

# история
async def history_cmd(update, context):
    data = await get_last(update.effective_user.id)

    if not data:
        await update.message.reply_text("📭 История пуста")
        return

    text = "\n\n".join([f"🔹 {q}\n{r[:100]}..." for q,r in data])

    await update.message.reply_text(text)

# WebApp data
async def webapp_data(update, context):
    data = update.effective_message.web_app_data.data

    result = await generate_prediction(data)

    await update.message.reply_text(result)

# main
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
import asyncio

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("🔮"), predict_start)],
        states={ASK: [MessageHandler(filters.TEXT, predict_answer)]},
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data))

    # 👇 вот ключевой момент
    async def on_startup(app):
        await init_db()

    app.post_init = on_startup

    app.run_polling()


if __name__ == "__main__":
    main()
