# bot.py - Main entry point

import os
import telebot
from config import BOT_TOKEN, UPLOAD_FOLDER
from database import init_db

# Create uploads folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# Shared session store across all handlers
shared_sessions = {}

# Initialize database
print("🔧 Initializing database...")
init_db()

# Register all handlers
from handlers.registration import register_handlers as reg_registration
from handlers.leave import register_handlers as reg_leave
from handlers.sick_note import register_handlers as reg_sick
from handlers.payslip import register_handlers as reg_payslip
from handlers.admin import register_handlers as reg_admin
from handlers.attendance import register_handlers as reg_attendance

reg_registration(bot)
reg_leave(bot, shared_sessions)
reg_sick(bot, shared_sessions)
reg_payslip(bot, shared_sessions)
reg_admin(bot, shared_sessions)
reg_attendance(bot)


# ── Fallback handler ─────────────────────────────────────────────

@bot.message_handler(func=lambda m: True)
def fallback(message):
    from database import get_worker_by_telegram_id
    uid = message.from_user.id
    worker = get_worker_by_telegram_id(uid)

    if not worker:
        bot.send_message(uid, "👋 សូមប្រើ /start ដើម្បីចុះឈ្មោះ។")
        return

    # Worker bot — always show worker menu only
    # Admin functions are in the separate Admin Bot
    from keyboards import main_menu_keyboard
    bot.send_message(uid, "សូមប្រើម៉ឺនុយខាងក្រោម:", reply_markup=main_menu_keyboard())


# ── Start polling ────────────────────────────────────────────────

if __name__ == "__main__":
    print("🤖 HR Bot is running...")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
