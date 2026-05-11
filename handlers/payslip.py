# handlers/payslip.py - ការបញ្ជូន/មើលបញ្ជីប្រាក់ខែ (Khmer)

from telebot import TeleBot
from database import (
    get_worker_by_telegram_id, save_payslip,
    get_payslips_by_worker, get_worker_by_employee_id
)
from keyboards import main_menu_keyboard, cancel_keyboard, admin_menu_keyboard
from states import PAYSLIP_EMP_ID, PAYSLIP_MONTH, PAYSLIP_FILE
from config import ADMIN_IDS

sessions = {}


def _is_admin(worker):
    return worker and (worker["is_admin"] or worker["telegram_id"] in ADMIN_IDS)


def register_handlers(bot: TeleBot, shared_sessions: dict):
    global sessions
    sessions = shared_sessions

    # ── អ្នកគ្រប់គ្រង: បញ្ជូនបញ្ជីប្រាក់ខែ ─────────────────────────────

    @bot.message_handler(func=lambda m: m.text == "💰 បញ្ជូនបញ្ជីប្រាក់ខែ")
    def start_send_payslip(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not _is_admin(worker):
            bot.send_message(uid, "⛔ សម្រាប់តែអ្នកគ្រប់គ្រងប៉ុណ្ណោះ។")
            return

        sessions[uid] = {"state": PAYSLIP_EMP_ID, "data": {}}
        bot.send_message(
            uid,
            "💰 *បញ្ជូនបញ្ជីប្រាក់ខែ*\n\nបញ្ចូល *លេខសម្គាល់បុគ្គលិក* ដែលត្រូវទទួល:",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )

    @bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == PAYSLIP_EMP_ID)
    def get_payslip_emp_id(message):
        uid = message.from_user.id
        if message.text == "❌ បោះបង់":
            sessions.pop(uid, None)
            bot.send_message(uid, "បានបោះបង់។", reply_markup=admin_menu_keyboard())
            return

        emp_id = message.text.strip().upper()
        target = get_worker_by_employee_id(emp_id)
        if not target:
            bot.send_message(uid, f"⚠️ រកមិនឃើញបុគ្គលិកដែលមានលេខ *{emp_id}*។ សូមព្យាយាមម្តងទៀត។",
                             parse_mode="Markdown")
            return

        sessions[uid]["data"]["target_worker"] = target
        sessions[uid]["state"] = PAYSLIP_MONTH
        bot.send_message(
            uid,
            f"✅ បានរក: *{target['full_name']}* ({target['department']})\n\n"
            f"បញ្ចូល *ខែ និងឆ្នាំ* នៃបញ្ជីប្រាក់ខែ (ឧ. May 2026):",
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == PAYSLIP_MONTH)
    def get_payslip_month(message):
        uid = message.from_user.id
        if message.text == "❌ បោះបង់":
            sessions.pop(uid, None)
            bot.send_message(uid, "បានបោះបង់។", reply_markup=admin_menu_keyboard())
            return

        month_str = message.text.strip()
        try:
            from datetime import datetime
            parsed = datetime.strptime(month_str, "%B %Y")
            sessions[uid]["data"]["month"] = parsed.strftime("%B")
            sessions[uid]["data"]["year"] = parsed.year
        except ValueError:
            bot.send_message(uid, "⚠️ ទម្រង់មិនត្រឹមត្រូវ។ សូមប្រើ 'Month YYYY' (ឧ. May 2026)។")
            return

        sessions[uid]["state"] = PAYSLIP_FILE
        bot.send_message(uid, "📎 សូមផ្ទុកឡើងឯកសារបញ្ជីប្រាក់ខែ (PDF ឬឯកសារ):")

    @bot.message_handler(
        content_types=["document"],
        func=lambda m: sessions.get(m.from_user.id, {}).get("state") == PAYSLIP_FILE
    )
    def get_payslip_file(message):
        uid = message.from_user.id
        data = sessions[uid]["data"]
        target = data["target_worker"]

        file_id = message.document.file_id
        file_name = message.document.file_name or "payslip.pdf"

        save_payslip(
            worker_id=target["id"],
            month=data["month"],
            year=data["year"],
            file_id=file_id,
            file_name=file_name
        )
        sessions.pop(uid, None)

        bot.send_message(
            uid,
            f"✅ បានបញ្ជូនបញ្ជីប្រាក់ខែទៅ *{target['full_name']}* សម្រាប់ *{data['month']} {data['year']}*។",
            parse_mode="Markdown",
            reply_markup=admin_menu_keyboard()
        )

        # ផ្ញើបញ្ជីប្រាក់ខែទៅបុគ្គលិក
        try:
            bot.send_document(
                target["telegram_id"],
                file_id,
                caption=(
                    f"💰 *បញ្ជីប្រាក់ខែរបស់អ្នក — {data['month']} {data['year']}*\n\n"
                    f"សូមរក្សាទុកឯកសារនេះ។"
                ),
                parse_mode="Markdown"
            )
            bot.send_message(
                target["telegram_id"],
                f"📬 បញ្ជីប្រាក់ខែសម្រាប់ *{data['month']} {data['year']}* ត្រូវបានផ្ញើមកអ្នករួចហើយ។",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        except Exception as e:
            bot.send_message(uid, f"⚠️ មិនអាចផ្ញើទៅបុគ្គលិកបានទេ: {e}")

    # ── បុគ្គលិក: មើលបញ្ជីប្រាក់ខែ ─────────────────────────────────────

    @bot.message_handler(func=lambda m: m.text == "💰 បញ្ជីប្រាក់ខែខ្ញុំ")
    def my_payslips(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not worker:
            bot.send_message(uid, "⚠️ សូមចុះឈ្មោះជាមុនសិន ដោយប្រើ /start")
            return

        slips = get_payslips_by_worker(worker["id"])
        if not slips:
            bot.send_message(uid, "💰 អ្នកមិនទាន់មានបញ្ជីប្រាក់ខែទេ។ វានឹងបង្ហាញនៅទីនេះនៅពេល HR ផ្ញើ។")
            return

        bot.send_message(uid, f"💰 *បញ្ជីប្រាក់ខែរបស់អ្នក ({len(slips)} សរុប):*", parse_mode="Markdown")
        for slip in slips[:12]:
            try:
                bot.send_document(
                    uid,
                    slip["file_id"],
                    caption=f"📄 បញ្ជីប្រាក់ខែ — {slip['month']} {slip['year']}"
                )
            except Exception:
                bot.send_message(uid, f"⚠️ មិនអាចទាញយកបញ្ជីប្រាក់ខែ {slip['month']} {slip['year']} បានទេ។")
