# handlers/sick_note.py - ការបញ្ជូនលិខិតឈឺ (Khmer)

from datetime import datetime
from telebot import TeleBot
from database import (
    get_worker_by_telegram_id, save_sick_note,
    get_sick_notes_by_worker, get_pending_sick_notes
)
from keyboards import main_menu_keyboard, cancel_keyboard, admin_menu_keyboard
from states import SICK_DATE, SICK_DESC, SICK_FILE
from config import ADMIN_IDS

sessions = {}


def _is_admin(worker):
    return worker and (worker["is_admin"] or worker["telegram_id"] in ADMIN_IDS)


def register_handlers(bot: TeleBot, shared_sessions: dict):
    global sessions
    sessions = shared_sessions

    # ── បុគ្គលិក: ចាប់ផ្តើមបញ្ជូនលិខិតឈឺ ───────────────────────────────

    @bot.message_handler(func=lambda m: m.text == "🤒 បញ្ជូនលិខិតឈឺ")
    def start_sick_note(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not worker:
            bot.send_message(uid, "⚠️ សូមចុះឈ្មោះជាមុនសិន ដោយប្រើ /start")
            return

        sessions[uid] = {"state": SICK_DATE, "data": {"worker_id": worker["id"]}}
        bot.send_message(
            uid,
            "🤒 *បញ្ជូនលិខិតឈឺ*\n\nបញ្ចូលកាលបរិច្ឆេទនៃលិខិតឈឺ (YYYY-MM-DD):",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )

    @bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == SICK_DATE)
    def get_sick_date(message):
        uid = message.from_user.id
        if message.text == "❌ បោះបង់":
            sessions.pop(uid, None)
            bot.send_message(uid, "បានបោះបង់។", reply_markup=main_menu_keyboard())
            return

        try:
            date = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
        except ValueError:
            bot.send_message(uid, "⚠️ ទម្រង់កាលបរិច្ឆេទមិនត្រឹមត្រូវ។ សូមប្រើ YYYY-MM-DD។")
            return

        sessions[uid]["data"]["note_date"] = str(date)
        sessions[uid]["state"] = SICK_DESC
        bot.send_message(uid, "📝 សូមពណ៌នាអំពីជំងឺ ឬស្ថានភាពសុខភាពរបស់អ្នក:")

    @bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == SICK_DESC)
    def get_sick_desc(message):
        uid = message.from_user.id
        if message.text == "❌ បោះបង់":
            sessions.pop(uid, None)
            bot.send_message(uid, "បានបោះបង់។", reply_markup=main_menu_keyboard())
            return

        sessions[uid]["data"]["description"] = message.text.strip()
        sessions[uid]["state"] = SICK_FILE
        bot.send_message(
            uid,
            "📎 សូមផ្ទុកឡើងឯកសារ ឬរូបថតលិខិតឈឺរបស់អ្នក។\n"
            "(ទទួលយក: PDF, រូបភាព, ឬឯកសារណាមួយ)"
        )

    @bot.message_handler(
        content_types=["document", "photo"],
        func=lambda m: sessions.get(m.from_user.id, {}).get("state") == SICK_FILE
    )
    def get_sick_file(message):
        uid = message.from_user.id
        data = sessions[uid]["data"]

        if message.content_type == "document":
            file_obj = message.document
            file_id = file_obj.file_id
            file_name = file_obj.file_name or "sick_note"
            file_type = "document"
        else:
            file_obj = message.photo[-1]
            file_id = file_obj.file_id
            file_name = f"sick_note_{data['note_date']}.jpg"
            file_type = "photo"

        note_id = save_sick_note(
            worker_id=data["worker_id"],
            file_id=file_id,
            file_name=file_name,
            file_type=file_type,
            note_date=data["note_date"],
            description=data["description"]
        )
        sessions.pop(uid, None)

        bot.send_message(
            uid,
            f"✅ *បានបញ្ជូនលិខិតឈឺ!*\n\n"
            f"📋 លេខយោង: #{note_id}\n"
            f"📅 កាលបរិច្ឆេទ: {data['note_date']}\n"
            f"📝 ការពណ៌នា: {data['description']}\n\n"
            f"ក្រុមការងារ HR នឹងពិនិត្យក្នុងពេលឆាប់ៗ។",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

        # ជូនដំណឹងអ្នកគ្រប់គ្រង
        worker = get_worker_by_telegram_id(uid)
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(
                    admin_id,
                    f"🔔 *លិខិតឈឺថ្មី* (#{note_id})\n\n"
                    f"👤 {worker['full_name']} ({worker['employee_id']})\n"
                    f"🏢 {worker['department']}\n"
                    f"📅 កាលបរិច្ឆេទ: {data['note_date']}\n"
                    f"📝 {data['description']}",
                    parse_mode="Markdown"
                )
                if file_type == "document":
                    bot.send_document(admin_id, file_id, caption=f"លិខិតឈឺពី {worker['full_name']}")
                else:
                    bot.send_photo(admin_id, file_id, caption=f"លិខិតឈឺពី {worker['full_name']}")
            except Exception:
                pass

    # ── អ្នកគ្រប់គ្រង: មើលលិខិតឈឺកំពុងរង់ចាំ ───────────────────────────

    @bot.message_handler(func=lambda m: m.text == "🤒 លិខិតឈឺកំពុងរង់ចាំ")
    def pending_sick_notes(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not _is_admin(worker):
            bot.send_message(uid, "⛔ សម្រាប់តែអ្នកគ្រប់គ្រងប៉ុណ្ណោះ។")
            return

        notes = get_pending_sick_notes()
        if not notes:
            bot.send_message(uid, "✅ មិនមានលិខិតឈឺកំពុងរង់ចាំទេ។")
            return

        for note in notes:
            caption = (
                f"🤒 *លិខិតឈឺ #{note['id']}*\n\n"
                f"👤 {note['full_name']} ({note['employee_id']})\n"
                f"🏢 {note['department']}\n"
                f"📅 កាលបរិច្ឆេទ: {note['note_date']}\n"
                f"📝 {note['description']}\n"
                f"🕐 បានផ្ទុក: {note['uploaded_at']}"
            )
            try:
                if note["file_type"] == "document":
                    bot.send_document(uid, note["file_id"], caption=caption, parse_mode="Markdown")
                else:
                    bot.send_photo(uid, note["file_id"], caption=caption, parse_mode="Markdown")
            except Exception:
                bot.send_message(uid, caption + "\n\n⚠️ មិនអាចទាញយកឯកសារបានទេ។", parse_mode="Markdown")
