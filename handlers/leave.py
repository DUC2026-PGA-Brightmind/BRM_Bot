# handlers/leave.py - ការស្នើសុំច្បាប់ (Khmer)

from datetime import datetime
from telebot import TeleBot
from database import (
    get_worker_by_telegram_id, create_leave_request,
    get_leave_requests_by_worker, get_pending_leave_requests,
    update_leave_status, get_leave_request_by_id
)
from keyboards import (
    main_menu_keyboard, cancel_keyboard,
    leave_type_keyboard, leave_action_keyboard, admin_menu_keyboard
)
from states import LEAVE_TYPE, LEAVE_START, LEAVE_END, LEAVE_REASON
from config import ADMIN_IDS

sessions = {}

LEAVE_TYPE_KH = {
    "annual": "ច្បាប់ប្រចាំឆ្នាំ",
    "sick": "ច្បាប់ឈឺ",
    "emergency": "ច្បាប់បន្ទាន់",
    "unpaid": "ច្បាប់គ្មានប្រាក់ខែ"
}

STATUS_KH = {
    "pending": "⏳ កំពុងរង់ចាំ",
    "approved": "✅ បានអនុម័ត",
    "rejected": "❌ បានបដិសេធ"
}


def _is_admin(worker):
    return worker and (worker["is_admin"] or worker["telegram_id"] in ADMIN_IDS)


def register_handlers(bot: TeleBot, shared_sessions: dict):
    global sessions
    sessions = shared_sessions

    # ── បុគ្គលិក: ចាប់ផ្តើមស្នើសុំច្បាប់ ──────────────────────────────

    @bot.message_handler(func=lambda m: m.text == "📅 ស្នើសុំច្បាប់")
    def start_leave(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not worker:
            bot.send_message(uid, "⚠️ សូមចុះឈ្មោះជាមុនសិន ដោយប្រើ /start")
            return

        sessions[uid] = {"state": LEAVE_TYPE, "data": {"worker_id": worker["id"]}}
        bot.send_message(
            uid,
            "📅 *ស្នើសុំច្បាប់ថ្មី*\n\nជ្រើសរើសប្រភេទច្បាប់:",
            parse_mode="Markdown",
            reply_markup=leave_type_keyboard()
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("ltype_"))
    def pick_leave_type(call):
        uid = call.from_user.id
        if sessions.get(uid, {}).get("state") != LEAVE_TYPE:
            bot.answer_callback_query(call.id, "វគ្គផុតកំណត់។ សូមប្រើម៉ឺនុយ។")
            return

        ltype = call.data.replace("ltype_", "")
        sessions[uid]["data"]["leave_type"] = ltype
        sessions[uid]["state"] = LEAVE_START

        bot.edit_message_text(
            f"ប្រភេទច្បាប់: *{LEAVE_TYPE_KH.get(ltype, ltype)}* ✅",
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown"
        )
        bot.send_message(
            uid,
            "📆 បញ្ចូល *កាលបរិច្ឆេទចាប់ផ្តើម* ច្បាប់ (ទម្រង់: YYYY-MM-DD):",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )
        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == LEAVE_START)
    def get_leave_start(message):
        uid = message.from_user.id
        if message.text == "❌ បោះបង់":
            sessions.pop(uid, None)
            bot.send_message(uid, "បានបោះបង់ការស្នើសុំច្បាប់។", reply_markup=main_menu_keyboard())
            return

        try:
            date = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
        except ValueError:
            bot.send_message(uid, "⚠️ ទម្រង់កាលបរិច្ឆេទមិនត្រឹមត្រូវ។ សូមប្រើ YYYY-MM-DD (ឧ. 2026-05-15)។")
            return

        sessions[uid]["data"]["start_date"] = str(date)
        sessions[uid]["state"] = LEAVE_END
        bot.send_message(uid, "📆 បញ្ចូល *កាលបរិច្ឆេទបញ្ចប់* ច្បាប់ (YYYY-MM-DD):",
                         parse_mode="Markdown")

    @bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == LEAVE_END)
    def get_leave_end(message):
        uid = message.from_user.id
        if message.text == "❌ បោះបង់":
            sessions.pop(uid, None)
            bot.send_message(uid, "បានបោះបង់ការស្នើសុំច្បាប់។", reply_markup=main_menu_keyboard())
            return

        try:
            date = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
        except ValueError:
            bot.send_message(uid, "⚠️ ទម្រង់កាលបរិច្ឆេទមិនត្រឹមត្រូវ។ សូមប្រើ YYYY-MM-DD។")
            return

        start = datetime.strptime(sessions[uid]["data"]["start_date"], "%Y-%m-%d").date()
        if date < start:
            bot.send_message(uid, "⚠️ កាលបរិច្ឆេទបញ្ចប់មិនអាចមុនកាលបរិច្ឆេទចាប់ផ្តើមបានទេ។")
            return

        sessions[uid]["data"]["end_date"] = str(date)
        sessions[uid]["state"] = LEAVE_REASON
        bot.send_message(uid, "📝 សូមពន្យល់ពីមូលហេតុនៃការស្នើសុំច្បាប់:")

    @bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == LEAVE_REASON)
    def get_leave_reason(message):
        uid = message.from_user.id
        if message.text == "❌ បោះបង់":
            sessions.pop(uid, None)
            bot.send_message(uid, "បានបោះបង់ការស្នើសុំច្បាប់។", reply_markup=main_menu_keyboard())
            return

        data = sessions[uid]["data"]
        data["reason"] = message.text.strip()

        req_id = create_leave_request(
            worker_id=data["worker_id"],
            leave_type=data["leave_type"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            reason=data["reason"]
        )
        sessions.pop(uid, None)

        bot.send_message(
            uid,
            f"✅ *បានបញ្ជូនការស្នើសុំច្បាប់!*\n\n"
            f"📋 លេខយោង: #{req_id}\n"
            f"🗂 ប្រភេទ: {LEAVE_TYPE_KH.get(data['leave_type'], data['leave_type'])}\n"
            f"📆 ពី: {data['start_date']} ដល់ {data['end_date']}\n"
            f"📝 មូលហេតុ: {data['reason']}\n\n"
            f"អ្នកនឹងទទួលបានការជូនដំណឹងនៅពេលត្រូវបានពិនិត្យ។",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

        # ជូនដំណឹងអ្នកគ្រប់គ្រង (សារ text ធម្មតា — ប្រើ Admin Bot ដើម្បីអនុម័ត)
        worker = get_worker_by_telegram_id(uid)
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(
                    admin_id,
                    f"🔔 *ការស្នើសុំច្បាប់ថ្មី* (#{req_id})\n\n"
                    f"👤 {worker['full_name']} ({worker['employee_id']})\n"
                    f"🏢 {worker['department']}\n"
                    f"🗂 ប្រភេទ: {LEAVE_TYPE_KH.get(data['leave_type'], data['leave_type'])}\n"
                    f"📆 {data['start_date']} ដល់ {data['end_date']}\n"
                    f"📝 {data['reason']}\n\n"
                    f"➡️ សូមចូល Admin Bot ដើម្បីអនុម័ត ឬ បដិសេធ",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    # ── បុគ្គលិក: មើលស្ថានភាពច្បាប់ ────────────────────────────────────

    @bot.message_handler(func=lambda m: m.text == "📋 ស្ថានភាពច្បាប់ខ្ញុំ")
    def my_leave_status(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not worker:
            bot.send_message(uid, "⚠️ សូមចុះឈ្មោះជាមុនសិន ដោយប្រើ /start")
            return

        requests = get_leave_requests_by_worker(worker["id"])
        if not requests:
            bot.send_message(uid, "អ្នកមិនទាន់មានការស្នើសុំច្បាប់ណាមួយទេ។")
            return

        text = "📋 *ការស្នើសុំច្បាប់របស់អ្នក:*\n\n"
        for r in requests[:10]:
            status_text = STATUS_KH.get(r["status"], r["status"])
            text += (
                f"*#{r['id']}* — {LEAVE_TYPE_KH.get(r['leave_type'], r['leave_type'])}\n"
                f"   📆 {r['start_date']} ដល់ {r['end_date']}\n"
                f"   ស្ថានភាព: {status_text}\n"
            )
            if r["admin_note"]:
                text += f"   💬 កំណត់ចំណាំ: {r['admin_note']}\n"
            text += "\n"

        bot.send_message(uid, text, parse_mode="Markdown")

    # ── អ្នកគ្រប់គ្រង: មើលច្បាប់កំពុងរង់ចាំ ───────────────────────────────

    @bot.message_handler(func=lambda m: m.text == "📋 ច្បាប់កំពុងរង់ចាំ")
    def pending_leaves(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not _is_admin(worker):
            bot.send_message(uid, "⛔ សម្រាប់តែអ្នកគ្រប់គ្រងប៉ុណ្ណោះ។")
            return

        requests = get_pending_leave_requests()
        if not requests:
            bot.send_message(uid, "✅ មិនមានការស្នើសុំច្បាប់កំពុងរង់ចាំទេ។")
            return

        for r in requests:
            text = (
                f"📋 *ការស្នើសុំច្បាប់ #{r['id']}*\n\n"
                f"👤 {r['full_name']} ({r['employee_id']})\n"
                f"🏢 {r['department']}\n"
                f"🗂 ប្រភេទ: {LEAVE_TYPE_KH.get(r['leave_type'], r['leave_type'])}\n"
                f"📆 {r['start_date']} ដល់ {r['end_date']}\n"
                f"📝 មូលហេតុ: {r['reason']}\n"
                f"🕐 បានបញ្ជូន: {r['created_at']}"
            )
            bot.send_message(uid, text, parse_mode="Markdown",
                             reply_markup=leave_action_keyboard(r["id"]))

    # ── អ្នកគ្រប់គ្រង: អនុម័ត / បដិសេធ ───────────────────────────────────

    @bot.callback_query_handler(func=lambda c: c.data.startswith("leave_approve_") or
                                                c.data.startswith("leave_reject_"))
    def handle_leave_decision(call):
        uid = call.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not _is_admin(worker):
            bot.answer_callback_query(call.id, "⛔ សម្រាប់តែអ្នកគ្រប់គ្រងប៉ុណ្ណោះ។")
            return

        parts = call.data.split("_")
        action = parts[1]
        leave_id = int(parts[2])

        status = "approved" if action == "approve" else "rejected"
        update_leave_status(leave_id, status)

        leave = get_leave_request_by_id(leave_id)
        icon = "✅" if status == "approved" else "❌"
        status_kh = "បានអនុម័ត" if status == "approved" else "បានបដិសេធ"

        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(uid, f"{icon} ការស្នើសុំច្បាប់ #{leave_id} *{status_kh}*។",
                         parse_mode="Markdown")

        # ជូនដំណឹងបុគ្គលិក
        if leave:
            try:
                bot.send_message(
                    leave["telegram_id"],
                    f"{icon} *ការស្នើសុំច្បាប់ #{leave_id} របស់អ្នក{status_kh}!*\n\n"
                    f"📆 {leave['start_date']} ដល់ {leave['end_date']}\n"
                    f"🗂 ប្រភេទ: {LEAVE_TYPE_KH.get(leave['leave_type'], leave['leave_type'])}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        bot.answer_callback_query(call.id, status_kh)
