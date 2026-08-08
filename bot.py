import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(format='%(asctime)s', level=logging.INFO)

# آدرس JSONBin (رایگان)
JSONBIN_API_KEY = os.getenv("$2a$10$F8VmD7JVotSYHhXT1SKvYOCfgT4AYl9yfeXlAAHyqYJpPQFVspcDu", "")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/6a7672c0f5f4af5e29f9ced8/latest"  # عوض کن
MINI_APP_URL = os.getenv('MINI_APP_URL', 'http://localhost:5000')

QUESTIONS = [
    {"question": "پایتخت ایران کجاست؟", "options": ["تهران", "مشهد", "اصفهان", "شیراز"], "correct": 0},
    {"question": "۱+۱ چند میشه؟", "options": ["۱", "۲", "۳", "۴"], "correct": 1},
    {"question": "رنگ آسمان چیست؟", "options": ["سبز", "آبی", "قرمز", "زرد"], "correct": 1},
    {"question": "بزرگترین سیاره؟", "options": ["زمین", "مریخ", "مشتری", "زحل"], "correct": 2},
]

# دریافت امتیاز از JSONBin
def get_score(user_id):
    try:
        response = requests.get(f"{JSONBIN_URL}", headers={"X-Master-Key": JSONBIN_API_KEY})
        data = response.json()
        return data.get("scores", {}).get(str(user_id), 0)
    except:
        return 0

# آپدیت امتیاز در JSONBin
def update_score(user_id, score):
    try:
        # دریافت دیتا فعلی
        response = requests.get(f"{JSONBIN_URL}", headers={"X-Master-Key": JSONBIN_API_KEY})
        data = response.json() if response.status_code == 200 else {"scores": {}}

        # آپدیت امتیاز
        data["scores"] = data.get("scores", {})
        data["scores"][str(user_id)] = data["scores"].get(str(user_id), 0) + score

        # ارسال به JSONBin
        requests.put(
            f"{JSONBIN_URL}",
            json=data,
            headers={"X-Master-Key": JSONBIN_API_KEY, "Content-Type": "application/json"}
        )
    except Exception as e:
        print(f"Error updating score: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("🎮 بازی کن", callback_data="play_game")],
        [InlineKeyboardButton("🏆 امتیاز من", callback_data="show_score")],
        [InlineKeyboardButton("🌐 مینی‌اپ", web_app="game")],
    ]
    await update.message.reply_text("🎉 به ربات بازی خوش آمدید!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    if query.data == "play_game":
        await start_game(update, context)
    elif query.data == "show_score":
        score = get_score(user_id)
        await query.edit_message_text(f"🏆 امتیاز شما: {score}")

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    context.user_data[user_id] = {"current_question": 0, "score": 0}
    await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = context.user_data.get(user_id, {})
    question_idx = user_data.get("current_question", 0)
    if question_idx >= len(QUESTIONS):
        score = user_data.get("score", 0)
        update_score(user_id, score)
        await update.message.reply_text("🎉 بازی تموم شد!")
        return
    question = QUESTIONS[question_idx]
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"answer_{i}") for i, opt in enumerate(question["options"])]]
    await update.message.reply_text(f"❓ سوال {question_idx + 1}: {question['question']}", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    if not query.data.startswith("answer_"): return
    answer_idx = int(query.data.split("_")[1])
    user_data = context.user_data.get(user_id, {})
    question_idx = user_data.get("current_question", 0)
    if question_idx >= len(QUESTIONS): return
    question = QUESTIONS[question_idx]
    if answer_idx == question["correct"]:
        user_data["score"] = user_data.get("score", 0) + 10
        await query.answer("✅ درست بود! +10 امتیاز", show_alert=True)
    else:
        await query.answer("❌ غلط بود!", show_alert=True)
    user_data["current_question"] = question_idx + 1
    context.user_data[user_id] = user_data
    await ask_question(update, context)

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.message.web_app_data.data
    user_id = str(update.effective_user.id)
    try:
        import json
        webapp_data = json.loads(data)
        if webapp_data.get("action") == "answer":
            if webapp_data.get("correct"):
                update_score(user_id, 10)
    except:
        pass

def run_bot():
    from dotenv import load_dotenv
    import os
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ توکن پیدا نشد!")
        return
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern=r"^answer_\d+"))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    print("🤖 ربات در حال اجرا...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
