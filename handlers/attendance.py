# handlers/attendance.py - វត្តមានបុគ្គលិក (Khmer)
# Check-in: 12 AM - 12 PM  |  Check-out: 12 PM - 12 AM

from datetime import datetime, date
from telebot import TeleBot
from database import (
    get_worker_by_telegram_id,
    check_in, check_out,
    get_attendance_by_worker,
    get_today_attendance
)
from keyboards import main_menu_keyboard

MONTHS_KH = {
    1:"មករា", 2:"កុម្ភៈ", 3:"មីនា", 4:"មេសា",
    5:"ឧសភា", 6:"មិថុនា", 7:"កក្កដា", 8:"សីហា",
    9:"កញ្ញា", 10:"តុលា", 11:"វិច្ឆិកា", 12:"ធ្នូ"
}

STATUS_KH = {
    "present":  "✅ ទាន់ម៉ោង",
    "late":     "⏰ យឺត",
    "absent":   "❌ អវត្តមាន",
    "half_day": "🌓 កន្លះថ្ងៃ"
}


def register_handlers(bot: TeleBot):

    # ── CHECK IN ─────────────────────────────────────────────────

    @bot.message_handler(func=lambda m: m.text == "🕐 ចូលធ្វើការ")
    def handle_check_in(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not worker:
            bot.send_message(uid, "⚠️ សូមចុះឈ្មោះជាមុនសិន ដោយប្រើ /start")
            return

        now = datetime.now()
        success, msg = check_in(worker["id"])

        if success:
            bot.send_message(
                uid,
                f"{msg}\n\n"
                f"👤 {worker['full_name']} ({worker['employee_id']})\n"
                f"🏢 {worker['department']}",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            bot.send_message(uid, msg, parse_mode="Markdown",
                             reply_markup=main_menu_keyboard())

    # ── CHECK OUT ────────────────────────────────────────────────

    @bot.message_handler(func=lambda m: m.text == "🕔 ចេញធ្វើការ")
    def handle_check_out(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not worker:
            bot.send_message(uid, "⚠️ សូមចុះឈ្មោះជាមុនសិន ដោយប្រើ /start")
            return

        success, msg = check_out(worker["id"])

        if success:
            bot.send_message(
                uid,
                f"{msg}\n\n"
                f"👤 {worker['full_name']} ({worker['employee_id']})\n"
                f"🏢 {worker['department']}",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            bot.send_message(uid, msg, parse_mode="Markdown",
                             reply_markup=main_menu_keyboard())

    # ── VIEW MY ATTENDANCE ───────────────────────────────────────

    @bot.message_handler(func=lambda m: m.text == "📆 វត្តមានខ្ញុំ")
    def my_attendance(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)
        if not worker:
            bot.send_message(uid, "⚠️ សូមចុះឈ្មោះជាមុនសិន ដោយប្រើ /start")
            return

        now = datetime.now()
        records = get_attendance_by_worker(worker["id"], now.month, now.year)

        # Today's status header
        today_rec = get_today_attendance(worker["id"])
        if today_rec:
            ci = today_rec["check_in"]
            co = today_rec["check_out"]
            ci_str = ci.strftime("%H:%M") if ci and hasattr(ci, "strftime") else "—"
            co_str = co.strftime("%H:%M") if co and hasattr(co, "strftime") else "—"
            today_text = (
                f"📍 *ថ្ងៃនេះ ({date.today()}):*\n"
                f"  🕐 ចូល: {ci_str}  |  🕔 ចេញ: {co_str}\n"
                f"  {STATUS_KH.get(today_rec['status'], today_rec['status'])}\n\n"
            )
        else:
            today_text = f"📍 *ថ្ងៃនេះ ({date.today()}):* មិនទាន់ចូលធ្វើការ\n\n"

        if not records:
            bot.send_message(
                uid,
                f"📆 *វត្តមានខ្ញុំ — {MONTHS_KH[now.month]} {now.year}*\n\n"
                f"{today_text}"
                f"មិនទាន់មានទិន្នន័យខែនេះ។",
                parse_mode="Markdown"
            )
            return

        # Count stats
        present = sum(1 for r in records if r["status"] == "present")
        late    = sum(1 for r in records if r["status"] == "late")
        absent  = sum(1 for r in records if r["status"] == "absent")

        text = (
            f"📆 *វត្តមានខ្ញុំ — {MONTHS_KH[now.month]} {now.year}*\n\n"
            f"{today_text}"
            f"📊 *សង្ខេបខែ:*\n"
            f"  ✅ ទាន់ម៉ោង: {present} ថ្ងៃ\n"
            f"  ⏰ យឺត: {late} ថ្ងៃ\n"
            f"  ❌ អវត្តមាន: {absent} ថ្ងៃ\n"
            f"  📋 សរុប: {len(records)} ថ្ងៃ\n\n"
            f"📅 *ប្រវត្តិ (១០ ថ្ងៃចុងក្រោយ):*\n"
        )

        for r in records[:10]:
            ci = r["check_in"]
            co = r["check_out"]
            ci_str = ci.strftime("%H:%M") if ci and hasattr(ci, "strftime") else "—"
            co_str = co.strftime("%H:%M") if co and hasattr(co, "strftime") else "—"
            st = STATUS_KH.get(r["status"], r["status"])
            text += f"  {r['work_date']} | ចូល {ci_str} ចេញ {co_str} | {st}\n"

        bot.send_message(uid, text, parse_mode="Markdown",
                         reply_markup=main_menu_keyboard())
