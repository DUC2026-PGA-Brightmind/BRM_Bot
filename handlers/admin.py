# handlers/admin.py - Worker bot: worker-only features (no HR admin access)
# All HR admin functions are in admin_bot.py (separate bot)

from telebot import TeleBot
from database import get_worker_by_telegram_id
from keyboards import main_menu_keyboard
from config import ADMIN_IDS


def register_handlers(bot: TeleBot, shared_sessions: dict):

    # ── /admin command — block it in worker bot ──────────────────

    @bot.message_handler(commands=["admin"])
    def block_admin_cmd(message):
        bot.send_message(
            message.from_user.id,
            "🔐 មុខងារ HR Admin មាននៅក្នុង *Admin Bot* ដាច់ដោយឡែក។\n"
            "សូមទាក់ទង HR ដើម្បីទទួលបាន Admin Bot link។",
            parse_mode="Markdown"
        )

    # ── Worker: view own profile ──────────────────────────────────

    @bot.message_handler(func=lambda m: m.text == "ℹ️ ប្រវត្តិរូបខ្ញុំ")
    def my_profile(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not worker:
            bot.send_message(uid, "⚠️ សូមចុះឈ្មោះជាមុនសិន ដោយប្រើ /start")
            return

        bot.send_message(
            uid,
            f"ℹ️ *ប្រវត្តិរូបរបស់អ្នក*\n\n"
            f"👤 ឈ្មោះ: {worker['full_name']}\n"
            f"🆔 លេខបុគ្គលិក: {worker['employee_id']}\n"
            f"🏢 នាយកដ្ឋាន: {worker['department']}\n"
            f"📞 ទូរស័ព្ទ: {worker['phone']}\n"
            f"📅 ថ្ងៃចុះឈ្មោះ: {worker['registered_at']}",
            parse_mode="Markdown"
        )

    # ── Block any HR admin buttons if somehow triggered ──────────

    @bot.message_handler(func=lambda m: m.text in [
        "📋 ច្បាប់កំពុងរង់ចាំ",
        "🤒 លិខិតឈឺកំពុងរង់ចាំ",
        "💰 បញ្ជូនបញ្ជីប្រាក់ខែ",
        "👥 បុគ្គលិកទាំងអស់",
        "📢 សារជូនដំណឹង",
        "🔙 ម៉ឺនុយបុគ្គលិក"
    ])
    def block_admin_buttons(message):
        uid = message.from_user.id
        bot.send_message(
            uid,
            "⛔ មុខងារនេះមានតែនៅក្នុង *Admin Bot* ប៉ុណ្ណោះ។",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
