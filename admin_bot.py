# admin_bot.py - Full Admin Bot (Khmer) with Employee Management,
# Leave Tracking, Payslip Upload, Reporting, Analytics, Export CSV/PDF

import os
import telebot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import ADMIN_BOT_TOKEN, BOT_TOKEN, ADMIN_IDS, EXPORT_FOLDER

# Worker bot instance — used to send messages to registered workers
# (workers only started worker bot, not admin bot)
worker_bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
from database import (
    get_worker_by_telegram_id, get_all_workers, get_worker_by_id,
    get_worker_by_employee_id, search_workers, get_departments,
    get_workers_by_department, update_worker, deactivate_worker,
    get_pending_leave_requests, get_all_leave_requests,
    update_leave_status, get_leave_request_by_id,
    get_pending_sick_notes, get_all_sick_notes,
    save_payslip, get_all_payslips,
    get_dashboard_stats, get_leave_analytics, get_worker_leave_summary
)
from export_utils import (
    export_workers_csv, export_leaves_csv, export_payslips_csv,
    export_leaves_pdf, export_workers_pdf
)
from states import (
    ADMIN_REJECT_NOTE, ADMIN_SEARCH, ADMIN_EDIT_FIELD, ADMIN_EDIT_VALUE,
    ADMIN_PAYSLIP_EMP, ADMIN_PAYSLIP_MONTH, ADMIN_PAYSLIP_FILE,
    ADMIN_BROADCAST, ADMIN_EXPORT_FILTER
)

os.makedirs(EXPORT_FOLDER, exist_ok=True)

bot = telebot.TeleBot(ADMIN_BOT_TOKEN, parse_mode=None)
sessions = {}  # {uid: {state, data}}

LEAVE_TYPE_KH = {
    "annual": "ច្បាប់ប្រចាំឆ្នាំ", "sick": "ច្បាប់ឈឺ",
    "emergency": "ច្បាប់បន្ទាន់", "unpaid": "ច្បាប់គ្មានប្រាក់ខែ"
}
STATUS_KH = {"pending": "⏳ រង់ចាំ", "approved": "✅ អនុម័ត", "rejected": "❌ បដិសេធ"}
MONTHS_KH = {
    1:"មករា",2:"កុម្ភៈ",3:"មីនា",4:"មេសា",5:"ឧសភា",6:"មិថុនា",
    7:"កក្កដា",8:"សីហា",9:"កញ្ញា",10:"តុលា",11:"វិច្ឆិកា",12:"ធ្នូ"
}


# ══════════════════════════════════════════════════════════════════
#  GUARD: only admins can use this bot
# ══════════════════════════════════════════════════════════════════

def is_admin(uid):
    return uid in ADMIN_IDS

def guard(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.from_user.id, "⛔ អ្នកមិនមានសិទ្ធិប្រើបូតនេះទេ។")
        return False
    return True

# ══════════════════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════════════════

def main_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("📊 ផ្ទាំងគ្រប់គ្រង"),
        KeyboardButton("👥 គ្រប់គ្រងបុគ្គលិក"),
        KeyboardButton("📅 គ្រប់គ្រងច្បាប់"),
        KeyboardButton("🤒 លិខិតឈឺ"),
        KeyboardButton("💰 បញ្ជីប្រាក់ខែ"),
        KeyboardButton("📈 របាយការណ៍ & វិភាគ"),
        KeyboardButton("📤 នាំចេញទិន្នន័យ"),
        KeyboardButton("📢 សារជូនដំណឹង")
    )
    return kb

def emp_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("🔍 ស្វែងរកបុគ្គលិក"),
        KeyboardButton("📋 បុគ្គលិកទាំងអស់"),
        KeyboardButton("🏢 តាមនាយកដ្ឋាន"),
        KeyboardButton("🔙 ត្រឡប់ក្រោយ")
    )
    return kb

def leave_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("⏳ ច្បាប់កំពុងរង់ចាំ"),
        KeyboardButton("✅ ច្បាប់បានអនុម័ត"),
        KeyboardButton("❌ ច្បាប់បានបដិសេធ"),
        KeyboardButton("📋 ច្បាប់ទាំងអស់"),
        KeyboardButton("🔙 ត្រឡប់ក្រោយ")
    )
    return kb

def report_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("📊 វិភាគច្បាប់"),
        KeyboardButton("👥 សង្ខេបបុគ្គលិក"),
        KeyboardButton("💰 របាយការណ៍ប្រាក់ខែ"),
        KeyboardButton("🔙 ត្រឡប់ក្រោយ")
    )
    return kb

def export_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("📄 CSV បុគ្គលិក"),
        KeyboardButton("📄 CSV ច្បាប់"),
        KeyboardButton("📄 CSV ប្រាក់ខែ"),
        KeyboardButton("🖨️ PDF បុគ្គលិក"),
        KeyboardButton("🖨️ PDF ច្បាប់"),
        KeyboardButton("🔙 ត្រឡប់ក្រោយ")
    )
    return kb

def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ បោះបង់"))
    return kb

def leave_action_kb(leave_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ អនុម័ត", callback_data=f"adm_approve_{leave_id}"),
        InlineKeyboardButton("❌ បដិសេធ", callback_data=f"adm_reject_{leave_id}")
    )
    return kb


# ══════════════════════════════════════════════════════════════════
#  /start  &  MAIN MENU
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "⛔ អ្នកមិនមានសិទ្ធិប្រើបូតនេះទេ។")
        return
    sessions.pop(uid, None)
    bot.send_message(
        uid,
        "🔑 *បន្ទប់គ្រប់គ្រង HR*\n\n"
        "សូមស្វាគមន៍! ជ្រើសរើសមុខងារខាងក្រោម:",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )

@bot.message_handler(func=lambda m: m.text == "🔙 ត្រឡប់ក្រោយ")
def go_back(message):
    if not guard(message): return
    sessions.pop(message.from_user.id, None)
    bot.send_message(message.from_user.id, "🏠 ម៉ឺនុយចម្បង:", reply_markup=main_kb())

# ══════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: m.text == "�� ផ្ទាំងគ្រប់គ្រង")
def dashboard(message):
    if not guard(message): return
    s = get_dashboard_stats()
    text = (
        "📊 *ផ្ទាំងគ្រប់គ្រង HR*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 បុគ្គលិកសរុប:          *{s['total_workers']}* នាក់\n"
        f"⏳ ច្បាប់កំពុងរង់ចាំ:      *{s['pending_leaves']}*\n"
        f"✅ ច្បាប់អនុម័តខែនេះ:     *{s['approved_this_month']}*\n"
        f"🤒 លិខិតឈឺរង់ចាំ:        *{s['pending_sick_notes']}*\n"
        f"💰 ប្រាក់ខែបានផ្ញើខែនេះ:  *{s['payslips_this_month']}*\n"
        f"📅 ច្បាប់ស្នើខែនេះ:       *{s['leaves_this_month']}*\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(message.from_user.id, text, parse_mode="Markdown")

# ══════════════════════════════════════════════════════════════════
#  EMPLOYEE MANAGEMENT
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: m.text == "👥 គ្រប់គ្រងបុគ្គលិក")
def emp_menu(message):
    if not guard(message): return
    bot.send_message(message.from_user.id, "👥 *គ្រប់គ្រងបុគ្គលិក*\nជ្រើសរើស:",
                     parse_mode="Markdown", reply_markup=emp_kb())

@bot.message_handler(func=lambda m: m.text == "📋 បុគ្គលិកទាំងអស់")
def all_workers(message):
    if not guard(message): return
    workers = get_all_workers()
    if not workers:
        bot.send_message(message.from_user.id, "មិនទាន់មានបុគ្គលិកទេ។")
        return
    text = f"👥 *បុគ្គលិកទាំងអស់ ({len(workers)} នាក់):*\n\n"
    for w in workers:
        text += (
            f"🆔 *{w['employee_id']}* — {w['full_name']}\n"
            f"   🏢 {w['department']} | 📞 {w['phone']}\n"
        )
        if len(text) > 3800:
            bot.send_message(message.from_user.id, text, parse_mode="Markdown")
            text = ""
    if text.strip():
        bot.send_message(message.from_user.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏢 តាមនាយកដ្ឋាន")
def by_dept(message):
    if not guard(message): return
    depts = get_departments()
    if not depts:
        bot.send_message(message.from_user.id, "មិនទាន់មាននាយកដ្ឋានទេ។")
        return
    kb = InlineKeyboardMarkup(row_width=2)
    for d in depts:
        kb.add(InlineKeyboardButton(f"🏢 {d}", callback_data=f"dept_{d[:30]}"))
    bot.send_message(message.from_user.id, "ជ្រើសរើសនាយកដ្ឋាន:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("dept_"))
def show_dept_workers(call):
    if not is_admin(call.from_user.id): return
    dept = call.data[5:]
    workers = get_workers_by_department(dept)
    text = f"🏢 *{dept}* — {len(workers)} នាក់\n\n"
    for w in workers:
        text += f"• *{w['full_name']}* ({w['employee_id']}) | 📞 {w['phone']}\n"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "🔍 ស្វែងរកបុគ្គលិក")
def search_start(message):
    if not guard(message): return
    sessions[message.from_user.id] = {"state": ADMIN_SEARCH}
    bot.send_message(message.from_user.id,
                     "🔍 បញ្ចូលឈ្មោះ, លេខបុគ្គលិក, ឬនាយកដ្ឋាន:",
                     reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == ADMIN_SEARCH)
def do_search(message):
    uid = message.from_user.id
    if message.text == "❌ បោះបង់":
        sessions.pop(uid, None)
        bot.send_message(uid, "បានបោះបង់។", reply_markup=emp_kb())
        return
    results = search_workers(message.text.strip())
    sessions.pop(uid, None)
    if not results:
        bot.send_message(uid, "🔍 រកមិនឃើញបុគ្គលិក។", reply_markup=emp_kb())
        return
    text = f"🔍 *លទ្ធផល ({len(results)} នាក់):*\n\n"
    kb = InlineKeyboardMarkup(row_width=1)
    for w in results[:10]:
        text += f"• *{w['full_name']}* ({w['employee_id']}) — {w['department']}\n"
        kb.add(InlineKeyboardButton(
            f"👤 {w['full_name']} ({w['employee_id']})",
            callback_data=f"viewemp_{w['id']}"
        ))
    bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("viewemp_"))
def view_employee(call):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.split("_")[1])
    w = get_worker_by_id(wid)
    if not w:
        bot.answer_callback_query(call.id, "រកមិនឃើញ។")
        return
    summary = get_worker_leave_summary(wid)
    leave_text = ""
    for s in summary:
        leave_text += f"  {LEAVE_TYPE_KH.get(s['leave_type'],s['leave_type'])} ({s['status']}): {s['count']} ដង, {s['days'] or 0} ថ្ងៃ\n"
    text = (
        f"👤 *{w['full_name']}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 លេខបុគ្គលិក: {w['employee_id']}\n"
        f"🏢 នាយកដ្ឋាន: {w['department']}\n"
        f"💼 តួនាទី: {w.get('position','—')}\n"
        f"📞 ទូរស័ព្ទ: {w['phone']}\n"
        f"💵 ប្រាក់ខែ: ${w.get('salary',0)}\n"
        f"📅 ថ្ងៃចូលធ្វើការ: {w.get('join_date','—')}\n"
        f"🟢 ស្ថានភាព: {'សកម្ម' if w.get('is_active',1) else 'អសកម្ម'}\n\n"
        f"📋 *ប្រវត្តិច្បាប់ (ឆ្នាំនេះ):*\n{leave_text or '  មិនទាន់មានទេ'}"
    )
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✏️ កែប្រែ", callback_data=f"editemp_{wid}"),
        InlineKeyboardButton("🚫 អសកម្ម", callback_data=f"deactivate_{wid}")
    )
    bot.send_message(call.from_user.id, text, parse_mode="Markdown", reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("deactivate_"))
def deactivate_emp(call):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.split("_")[1])
    deactivate_worker(wid)
    bot.answer_callback_query(call.id, "បានកំណត់ជាអសកម្ម។")
    bot.send_message(call.from_user.id, "✅ បុគ្គលិកត្រូវបានកំណត់ជាអសកម្ម។")

@bot.callback_query_handler(func=lambda c: c.data.startswith("editemp_"))
def edit_emp_start(call):
    if not is_admin(call.from_user.id): return
    wid = int(call.data.split("_")[1])
    w = get_worker_by_id(wid)
    sessions[call.from_user.id] = {"state": ADMIN_EDIT_FIELD, "data": {"worker": w}}
    kb = InlineKeyboardMarkup(row_width=2)
    for field, label in [("full_name","ឈ្មោះ"),("department","នាយកដ្ឋាន"),
                          ("phone","ទូរស័ព្ទ"),("position","តួនាទី"),
                          ("salary","ប្រាក់ខែ"),("join_date","ថ្ងៃចូលធ្វើការ")]:
        kb.add(InlineKeyboardButton(f"✏️ {label}", callback_data=f"editfield_{field}"))
    bot.send_message(call.from_user.id,
                     f"✏️ *កែប្រែ {w['full_name']}*\nជ្រើសរើសវាលដែលចង់កែ:",
                     parse_mode="Markdown", reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("editfield_"))
def edit_field_pick(call):
    uid = call.from_user.id
    if not is_admin(uid): return
    field = call.data.split("_")[1]
    if uid not in sessions: return
    sessions[uid]["data"]["field"] = field
    sessions[uid]["state"] = ADMIN_EDIT_VALUE
    labels = {"full_name":"ឈ្មោះ","department":"នាយកដ្ឋាន","phone":"ទូរស័ព្ទ",
              "position":"តួនាទី","salary":"ប្រាក់ខែ","join_date":"ថ្ងៃចូលធ្វើការ (YYYY-MM-DD)"}
    bot.send_message(uid, f"បញ្ចូលតម្លៃថ្មីសម្រាប់ *{labels.get(field,field)}*:",
                     parse_mode="Markdown", reply_markup=cancel_kb())
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == ADMIN_EDIT_VALUE)
def edit_field_save(message):
    uid = message.from_user.id
    if message.text == "❌ បោះបង់":
        sessions.pop(uid, None)
        bot.send_message(uid, "បានបោះបង់។", reply_markup=emp_kb())
        return
    sess = sessions.pop(uid, {})
    w = sess["data"]["worker"]
    field = sess["data"]["field"]
    val = message.text.strip()
    w[field] = val
    try:
        update_worker(w["id"], w.get("full_name",""), w.get("department",""),
                      w.get("phone",""), w.get("position",""),
                      w.get("salary",0), w.get("join_date",None))
        bot.send_message(uid, f"✅ បានកែប្រែ *{field}* ជា *{val}* ។",
                         parse_mode="Markdown", reply_markup=emp_kb())
    except Exception as e:
        bot.send_message(uid, f"❌ កំហុស: {e}", reply_markup=emp_kb())


# ══════════════════════════════════════════════════════════════════
#  LEAVE MANAGEMENT
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: m.text == "📅 គ្រប់គ្រងច្បាប់")
def leave_menu(message):
    if not guard(message): return
    bot.send_message(message.from_user.id, "📅 *គ្រប់គ្រងច្បាប់*\nជ្រើសរើស:",
                     parse_mode="Markdown", reply_markup=leave_kb())

@bot.message_handler(func=lambda m: m.text == "⏳ ច្បាប់កំពុងរង់ចាំ")
def pending_leaves(message):
    if not guard(message): return
    reqs = get_pending_leave_requests()
    if not reqs:
        bot.send_message(message.from_user.id, "✅ មិនមានច្បាប់កំពុងរង់ចាំទេ។")
        return
    bot.send_message(message.from_user.id, f"⏳ *ច្បាប់កំពុងរង់ចាំ ({len(reqs)}):*", parse_mode="Markdown")
    for r in reqs:
        try:
            days = (r["end_date"] - r["start_date"]).days + 1
        except Exception:
            days = "?"
        text = (
            f"📋 *ច្បាប់ #{r['id']}*\n"
            f"👤 {r['full_name']} ({r['employee_id']})\n"
            f"🏢 {r['department']}\n"
            f"�� {LEAVE_TYPE_KH.get(r['leave_type'],r['leave_type'])}\n"
            f"📆 {r['start_date']} → {r['end_date']} ({days} ថ្ងៃ)\n"
            f"📝 {r['reason']}\n"
            f"🕐 {r['created_at']}"
        )
        bot.send_message(message.from_user.id, text, parse_mode="Markdown",
                         reply_markup=leave_action_kb(r["id"]))

@bot.message_handler(func=lambda m: m.text in ["✅ ច្បាប់បានអនុម័ត","❌ ច្បាប់បានបដិសេធ","📋 ច្បាប់ទាំងអស់"])
def view_leaves_by_status(message):
    if not guard(message): return
    status_map = {"✅ ច្បាប់បានអនុម័ត":"approved","❌ ច្បាប់បានបដិសេធ":"rejected","📋 ច្បាប់ទាំងអស់":None}
    status = status_map.get(message.text)
    reqs = get_all_leave_requests(status=status)
    if not reqs:
        bot.send_message(message.from_user.id, "មិនមានទិន្នន័យ។")
        return
    text = f"📋 *ច្បាប់ ({len(reqs)}):*\n\n"
    for r in reqs[:20]:
        st = STATUS_KH.get(r["status"], r["status"])
        text += f"#{r['id']} {r['full_name']} | {LEAVE_TYPE_KH.get(r['leave_type'],r['leave_type'])} | {r['start_date']} | {st}\n"
        if len(text) > 3800:
            bot.send_message(message.from_user.id, text, parse_mode="Markdown")
            text = ""
    if text.strip():
        bot.send_message(message.from_user.id, text, parse_mode="Markdown")

# Approve / Reject via inline buttons
@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_approve_") or c.data.startswith("adm_reject_"))
def handle_leave_action(call):
    uid = call.from_user.id
    if not is_admin(uid):
        bot.answer_callback_query(call.id, "⛔ គ្មានសិទ្ធិ")
        return
    # adm_approve_5  →  action="approve", leave_id=5
    # adm_reject_5   →  action="reject",  leave_id=5
    try:
        _, action, leave_id_str = call.data.split("_", 2)
        leave_id = int(leave_id_str)
    except (ValueError, IndexError):
        bot.answer_callback_query(call.id, "❌ callback data ខុស")
        return

    if action == "reject":
        sessions[uid] = {"state": ADMIN_REJECT_NOTE, "data": {"leave_id": leave_id}}
        bot.send_message(uid, f"📝 បញ្ចូលមូលហេតុបដិសេធច្បាប់ #{leave_id} (ឬវាយ '-' ដើម្បីរំលង):",
                         reply_markup=cancel_kb())
        bot.answer_callback_query(call.id)
        return

    update_leave_status(leave_id, "approved", reviewed_by=uid)
    leave = get_leave_request_by_id(leave_id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(uid, f"✅ ច្បាប់ #{leave_id} *បានអនុម័ត*។", parse_mode="Markdown")
    if leave:
        try:
            # ប្រើ worker_bot ផ្ញើ ព្រោះ worker បានចុះឈ្មោះតាម worker bot
            worker_bot.send_message(
                leave["telegram_id"],
                f"✅ *ច្បាប់ #{leave_id} របស់អ្នកបានអនុម័ត!*\n"
                f"📆 {leave['start_date']} → {leave['end_date']}\n"
                f"🗂 {LEAVE_TYPE_KH.get(leave['leave_type'],leave['leave_type'])}",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    bot.answer_callback_query(call.id, "បានអនុម័ត")

@bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == ADMIN_REJECT_NOTE)
def reject_with_note(message):
    uid = message.from_user.id
    if message.text == "❌ បោះបង់":
        sessions.pop(uid, None)
        bot.send_message(uid, "បានបោះបង់។", reply_markup=leave_kb())
        return
    sess = sessions.pop(uid, {})
    leave_id = sess["data"]["leave_id"]
    note = message.text.strip() if message.text.strip() != "-" else ""
    update_leave_status(leave_id, "rejected", admin_note=note, reviewed_by=uid)
    leave = get_leave_request_by_id(leave_id)
    bot.send_message(uid, f"❌ ច្បាប់ #{leave_id} *បានបដិសេធ*។", parse_mode="Markdown", reply_markup=leave_kb())
    if leave:
        try:
            msg = f"❌ *ច្បាប់ #{leave_id} របស់អ្នកបានបដិសេធ។*\n📆 {leave['start_date']} → {leave['end_date']}"
            if note:
                msg += f"\n💬 មូលហេតុ: {note}"
            # ប្រើ worker_bot ផ្ញើ ព្រោះ worker បានចុះឈ្មោះតាម worker bot
            worker_bot.send_message(leave["telegram_id"], msg, parse_mode="Markdown")
        except Exception:
            pass

# ══════════════════════════════════════════════════════════════════
#  SICK NOTES
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: m.text == "🤒 លិខិតឈឺ")
def sick_notes_menu(message):
    if not guard(message): return
    notes = get_pending_sick_notes()
    all_notes = get_all_sick_notes()
    text = (
        f"🤒 *លិខិតឈឺ*\n\n"
        f"⏳ កំពុងរង់ចាំ: *{len(notes)}*\n"
        f"📋 សរុបទាំងអស់: *{len(all_notes)}*"
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("⏳ មើលលិខិតឈឺរង់ចាំ", callback_data="sick_pending"))
    kb.add(InlineKeyboardButton("📋 មើលទាំងអស់", callback_data="sick_all"))
    bot.send_message(message.from_user.id, text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ["sick_pending","sick_all"])
def show_sick_notes(call):
    if not is_admin(call.from_user.id): return
    notes = get_pending_sick_notes() if call.data == "sick_pending" else get_all_sick_notes()
    if not notes:
        bot.answer_callback_query(call.id, "មិនមានទិន្នន័យ។")
        return
    bot.answer_callback_query(call.id)
    for note in notes[:10]:
        caption = (
            f"🤒 *លិខិតឈឺ #{note['id']}*\n"
            f"👤 {note['full_name']} ({note['employee_id']})\n"
            f"🏢 {note['department']}\n"
            f"📅 {note['note_date']}\n"
            f"📝 {note['description']}\n"
            f"🕐 {note['uploaded_at']}"
        )
        try:
            if note["file_type"] == "document":
                bot.send_document(call.from_user.id, note["file_id"], caption=caption, parse_mode="Markdown")
            else:
                bot.send_photo(call.from_user.id, note["file_id"], caption=caption, parse_mode="Markdown")
        except Exception:
            bot.send_message(call.from_user.id, caption + "\n⚠️ ឯកសាររកមិនឃើញ។", parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════
#  PAYSLIP MANAGEMENT
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: m.text == "💰 បញ្ជីប្រាក់ខែ")
def payslip_menu(message):
    if not guard(message): return
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📤 បញ្ជូនប្រាក់ខែទៅបុគ្គលិក", callback_data="payslip_send"),
        InlineKeyboardButton("📋 មើលប្រាក់ខែទាំងអស់", callback_data="payslip_all")
    )
    bot.send_message(message.from_user.id, "💰 *គ្រប់គ្រងបញ្ជីប្រាក់ខែ*\nជ្រើសរើស:",
                     parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "payslip_send")
def payslip_send_start(call):
    uid = call.from_user.id
    if not is_admin(uid): return
    sessions[uid] = {"state": ADMIN_PAYSLIP_EMP, "data": {}}
    bot.send_message(uid, "💰 *បញ្ជូនបញ្ជីប្រាក់ខែ*\n\nបញ្ចូល *លេខបុគ្គលិក* (ឧ. EMP001) ឬ ALL សម្រាប់ទាំងអស់:",
                     parse_mode="Markdown", reply_markup=cancel_kb())
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == ADMIN_PAYSLIP_EMP)
def payslip_get_emp(message):
    uid = message.from_user.id
    if message.text == "❌ បោះបង់":
        sessions.pop(uid, None)
        bot.send_message(uid, "បានបោះបង់។", reply_markup=main_kb())
        return
    emp_input = message.text.strip().upper()
    if emp_input == "ALL":
        sessions[uid]["data"]["target"] = "ALL"
        sessions[uid]["data"]["target_name"] = "បុគ្គលិកទាំងអស់"
    else:
        w = get_worker_by_employee_id(emp_input)
        if not w:
            bot.send_message(uid, f"⚠️ រកមិនឃើញ *{emp_input}*។ ព្យាយាមម្តងទៀត:", parse_mode="Markdown")
            return
        sessions[uid]["data"]["target"] = w
        sessions[uid]["data"]["target_name"] = w["full_name"]
    sessions[uid]["state"] = ADMIN_PAYSLIP_MONTH
    bot.send_message(uid,
                     f"✅ គោលដៅ: *{sessions[uid]['data']['target_name']}*\n\nបញ្ចូលខែ និងឆ្នាំ (ឧ. May 2026):",
                     parse_mode="Markdown")

@bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == ADMIN_PAYSLIP_MONTH)
def payslip_get_month(message):
    uid = message.from_user.id
    if message.text == "❌ បោះបង់":
        sessions.pop(uid, None)
        bot.send_message(uid, "បានបោះបង់។", reply_markup=main_kb())
        return
    try:
        from datetime import datetime
        parsed = datetime.strptime(message.text.strip(), "%B %Y")
        sessions[uid]["data"]["month"] = parsed.strftime("%B")
        sessions[uid]["data"]["year"] = parsed.year
    except ValueError:
        bot.send_message(uid, "⚠️ ទម្រង់មិនត្រឹមត្រូវ។ ឧ. May 2026")
        return
    sessions[uid]["state"] = ADMIN_PAYSLIP_FILE
    bot.send_message(uid, "📎 ផ្ទុកឡើងឯកសារបញ្ជីប្រាក់ខែ (PDF):")

@bot.message_handler(content_types=["document"],
                     func=lambda m: sessions.get(m.from_user.id, {}).get("state") == ADMIN_PAYSLIP_FILE)
def payslip_get_file(message):
    uid = message.from_user.id
    data = sessions.pop(uid, {}).get("data", {})
    file_id = message.document.file_id
    file_name = message.document.file_name or "payslip.pdf"
    month = data.get("month","")
    year = data.get("year","")
    target = data.get("target")

    if target == "ALL":
        workers = get_all_workers()
        sent = 0
        failed = 0
        progress_msg = bot.send_message(uid, f"⏳ កំពុងផ្ញើប្រាក់ខែទៅ {len(workers)} នាក់...")
        for w in workers:
            try:
                save_payslip(w["id"], month, year, file_id, file_name)
                # ប្រើ worker_bot ផ្ញើ ព្រោះ workers ចុះឈ្មោះតាម worker bot
                worker_bot.send_document(
                    w["telegram_id"], file_id,
                    caption=f"💰 *បញ្ជីប្រាក់ខែ — {month} {year}*",
                    parse_mode="Markdown"
                )
                sent += 1
            except Exception:
                failed += 1
        try:
            bot.delete_message(uid, progress_msg.message_id)
        except Exception:
            pass
        bot.send_message(
            uid,
            f"✅ *ផ្ញើប្រាក់ខែបានបញ្ចប់!*\n\n"
            f"📤 បានផ្ញើ: *{sent}* នាក់\n"
            f"❌ បរាជ័យ: *{failed}* នាក់\n"
            f"📅 ខែ: {month} {year}",
            parse_mode="Markdown", reply_markup=main_kb()
        )
    else:
        save_payslip(target["id"], month, year, file_id, file_name)
        try:
            # ប្រើ worker_bot ផ្ញើ ព្រោះ worker ចុះឈ្មោះតាម worker bot
            worker_bot.send_document(
                target["telegram_id"], file_id,
                caption=f"💰 *បញ្ជីប្រាក់ខែ — {month} {year}*",
                parse_mode="Markdown"
            )
            worker_bot.send_message(
                target["telegram_id"],
                f"📬 បញ្ជីប្រាក់ខែ *{month} {year}* ត្រូវបានផ្ញើមកអ្នករួចហើយ។",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        bot.send_message(
            uid,
            f"✅ បានផ្ញើប្រាក់ខែ *{month} {year}* ទៅ *{target['full_name']}* ។",
            parse_mode="Markdown", reply_markup=main_kb()
        )

@bot.callback_query_handler(func=lambda c: c.data == "payslip_all")
def view_all_payslips(call):
    if not is_admin(call.from_user.id): return
    slips = get_all_payslips()
    if not slips:
        bot.answer_callback_query(call.id, "មិនមានទិន្នន័យ។")
        return
    text = f"💰 *បញ្ជីប្រាក់ខែទាំងអស់ ({len(slips)}):*\n\n"
    for s in slips[:20]:
        text += f"• {s['full_name']} ({s['employee_id']}) — {s['month']} {s['year']}\n"
    bot.send_message(call.from_user.id, text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# ══════════════════════════════════════════════════════════════════
#  REPORTS & ANALYTICS
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: m.text == "📈 របាយការណ៍ & វិភាគ")
def report_menu(message):
    if not guard(message): return
    bot.send_message(message.from_user.id, "📈 *របាយការណ៍ & វិភាគ*\nជ្រើសរើស:",
                     parse_mode="Markdown", reply_markup=report_kb())

@bot.message_handler(func=lambda m: m.text == "📊 វិភាគច្បាប់")
def leave_analytics(message):
    if not guard(message): return
    from datetime import datetime
    data = get_leave_analytics()
    year = data["year"]
    MONTHS_EN = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                 7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

    text = f"📊 *វិភាគច្បាប់ — ឆ្នាំ {year}*\n\n"

    text += "📌 *តាមប្រភេទ:*\n"
    for r in data["by_type"]:
        text += (f"  {LEAVE_TYPE_KH.get(r['leave_type'],r['leave_type'])}: "
                 f"សរុប {r['total']} | ✅{r['approved']} ❌{r['rejected']} ⏳{r['pending']}\n")

    text += "\n🏢 *តាមនាយកដ្ឋាន:*\n"
    for r in data["by_dept"][:8]:
        text += f"  {r['department']}: {r['total']} ស្នើ ({r['approved']} អនុម័ត)\n"

    text += "\n📅 *តាមខែ:*\n"
    for r in data["by_month"]:
        bar = "█" * min(r["total"], 15)
        text += f"  {MONTHS_EN.get(r['month'],r['month'])}: {bar} {r['total']}\n"

    text += "\n🏆 *ច្រើនច្បាប់បំផុត (Top 5):*\n"
    for i, r in enumerate(data["top_takers"][:5], 1):
        text += f"  {i}. {r['full_name']} ({r['employee_id']}) — {r['total_days']} ថ្ងៃ\n"

    bot.send_message(message.from_user.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👥 សង្ខេបបុគ្គលិក")
def worker_summary(message):
    if not guard(message): return
    workers = get_all_workers()
    depts = {}
    for w in workers:
        d = w.get("department","Unknown")
        depts[d] = depts.get(d, 0) + 1
    text = f"👥 *សង្ខេបបុគ្គលិក*\n\nសរុប: *{len(workers)}* នាក់\n\n🏢 *តាមនាយកដ្ឋាន:*\n"
    for dept, count in sorted(depts.items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 20)
        text += f"  {dept}: {bar} {count}\n"
    bot.send_message(message.from_user.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💰 របាយការណ៍ប្រាក់ខែ")
def payslip_report(message):
    if not guard(message): return
    slips = get_all_payslips()
    by_month = {}
    for s in slips:
        key = f"{s['month']} {s['year']}"
        by_month[key] = by_month.get(key, 0) + 1
    text = f"💰 *របាយការណ៍ប្រាក់ខែ*\n\nសរុបបានផ្ញើ: *{len(slips)}*\n\n📅 *តាមខែ:*\n"
    for k, v in sorted(by_month.items(), reverse=True)[:12]:
        text += f"  {k}: {v} នាក់\n"
    bot.send_message(message.from_user.id, text, parse_mode="Markdown")



# ══════════════════════════════════════════════════════════════════
#  REPORTS AND ANALYTICS
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: m.text == "📈 របាយការណ៍ & វិភាគ")
def report_menu(message):
    if not guard(message): return
    bot.send_message(message.from_user.id, "📈 *របាយការណ៍*",
                     parse_mode="Markdown", reply_markup=report_kb())

@bot.message_handler(func=lambda m: m.text == "📊 វិភាគច្បាប់")
def leave_analytics_cmd(message):
    if not guard(message): return
    data = get_leave_analytics()
    year = data["year"]
    MONTHS_EN = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                 7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    text = f"📊 *វិភាគច្បាប់ — ឆ្នាម {year}*\n\n"
    text += "📌 *តាមប្រភេត:*\n"
    for r in data["by_type"]:
        lname = LEAVE_TYPE_KH.get(r["leave_type"], r["leave_type"])
        text += f"  {lname}: សរុប {r['total']} | ✅{r['approved']} ❌{r['rejected']} ⏳{r['pending']}\n"
    text += "\n🏢 *តាមនាយកដ្ឋាន:*\n"
    for r in data["by_dept"][:6]:
        text += f"  {r['department']}: {r['total']} ({r['approved']} អនុម័ត)\n"
    text += "\n📅 *តាមខែ:*\n"
    for r in data["by_month"]:
        bar = chr(0x2588) * min(r["total"], 12)
        text += f"  {MONTHS_EN.get(r['month'], str(r['month']))}: {bar} {r['total']}\n"
    text += "\n🏆 *Top 5 ច្រើនច្បាប់:*\n"
    for i, r in enumerate(data["top_takers"][:5], 1):
        text += f"  {i}. {r['full_name']} ({r['employee_id']}) — {r['total_days']} ថ្ង្\n"
    bot.send_message(message.from_user.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👥 សង្ខេបបុគ្គលិក")
def worker_summary_cmd(message):
    if not guard(message): return
    workers = get_all_workers()
    depts = {}
    for w in workers:
        d = w.get("department", "Unknown")
        depts[d] = depts.get(d, 0) + 1
    text = f"👥 *សង្ខេបបុគ្គលិក*\n\nសរុប: *{len(workers)}* នាក\n\n🏢 *តាមនាយកដ្ឋាន:*\n"
    for dept, count in sorted(depts.items(), key=lambda x: -x[1]):
        bar = chr(0x2588) * min(count, 20)
        text += f"  {dept}: {bar} {count}\n"
    bot.send_message(message.from_user.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💰 របាយការណ៍ប្រាក្ខែ")
def payslip_report_cmd(message):
    if not guard(message): return
    slips = get_all_payslips()
    by_month = {}
    for s in slips:
        key = f"{s['month']} {s['year']}"
        by_month[key] = by_month.get(key, 0) + 1
    text = f"💰 *របាយការណ៍ប្រាក្ខែ*\n\nសរុប: *{len(slips)}*\n\n📅 *តាមខែ:*\n"
    for k, v in sorted(by_month.items(), reverse=True)[:12]:
        text += f"  {k}: {v} នាក\n"
    bot.send_message(message.from_user.id, text, parse_mode="Markdown")

# ══════════════════════════════════════════════════════════════════
#  EXPORT CSV / PDF
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: m.text == "📤 នាមចេញតិន្នន័យ")
def export_menu(message):
    if not guard(message): return
    bot.send_message(message.from_user.id, "📤 *នាមចេញតិន្នន័យ*",
                     parse_mode="Markdown", reply_markup=export_kb())

@bot.message_handler(func=lambda m: m.text == "📄 CSV បុគ្គលិក")
def export_workers_csv_cmd(message):
    if not guard(message): return
    workers = get_all_workers()
    path = export_workers_csv(workers)
    with open(path, "rb") as f:
        bot.send_document(message.from_user.id, f, caption=f"📄 CSV បុគ្គលិក {len(workers)} នាក")
    os.remove(path)

@bot.message_handler(func=lambda m: m.text == "📄 CSV ច្បាប់")
def export_leaves_csv_cmd(message):
    if not guard(message): return
    leaves = get_all_leave_requests()
    path = export_leaves_csv(leaves)
    with open(path, "rb") as f:
        bot.send_document(message.from_user.id, f, caption=f"📄 CSV ច្បាប់ {len(leaves)} កំណត់")
    os.remove(path)

@bot.message_handler(func=lambda m: m.text == "📄 CSV ប្រាក្ខែ")
def export_payslips_csv_cmd(message):
    if not guard(message): return
    slips = get_all_payslips()
    path = export_payslips_csv(slips)
    with open(path, "rb") as f:
        bot.send_document(message.from_user.id, f, caption=f"📄 CSV ប្រាក្ខែ {len(slips)} កំណត់")
    os.remove(path)

@bot.message_handler(func=lambda m: m.text == "🖨️ PDF បុគ្គលិក")
def export_workers_pdf_cmd(message):
    if not guard(message): return
    workers = get_all_workers()
    path = export_workers_pdf(workers, title="Employee Report")
    with open(path, "rb") as f:
        bot.send_document(message.from_user.id, f, caption=f"🖨️ PDF បុគ្គលិក {len(workers)} នាក")
    os.remove(path)

@bot.message_handler(func=lambda m: m.text == "🖨️ PDF ច្បាប់")
def export_leaves_pdf_cmd(message):
    if not guard(message): return
    leaves = get_all_leave_requests()
    path = export_leaves_pdf(leaves, title="Leave Requests Report")
    with open(path, "rb") as f:
        bot.send_document(message.from_user.id, f, caption=f"🖨️ PDF ច្បាប់ {len(leaves)} កំណត់")
    os.remove(path)

# ══════════════════════════════════════════════════════════════════
#  BROADCAST
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: m.text == "📢 សារជូនដំណឹង")
def broadcast_start(message):
    if not guard(message): return
    sessions[message.from_user.id] = {"state": ADMIN_BROADCAST}
    bot.send_message(
        message.from_user.id,
        "📢 *សារជូនដំណឹង*\n\n"
        "សរសេរសារដែលចង់ផ្ញើទៅបុគ្គលិក *ទាំងអស់* ដែលបានចុះឈ្មោះ:\n\n"
        "_(ចុច ❌ បោះបង់ ដើម្បីបោះបង់)_",
        parse_mode="Markdown",
        reply_markup=cancel_kb()
    )

@bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == ADMIN_BROADCAST)
def broadcast_send(message):
    uid = message.from_user.id
    if message.text == "❌ បោះបង់":
        sessions.pop(uid, None)
        bot.send_message(uid, "បានបោះបង់ការផ្ញើសារ។", reply_markup=main_kb())
        return

    text = message.text.strip()
    sessions.pop(uid, None)

    # ផ្ញើ progress message
    progress_msg = bot.send_message(uid, "⏳ កំពុងផ្ញើសារ...")

    workers = get_all_workers()
    sent = 0
    failed = 0
    failed_names = []

    for w in workers:
        try:
            # ប្រើ worker_bot ផ្ញើ ព្រោះ workers បានចុះឈ្មោះតាម worker bot
            worker_bot.send_message(
                w["telegram_id"],
                f"📢 *សារជូនដំណឹងពី HR:*\n\n{text}",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception as e:
            failed += 1
            failed_names.append(f"{w['full_name']} ({w['employee_id']})")

    # លុប progress message
    try:
        bot.delete_message(uid, progress_msg.message_id)
    except Exception:
        pass

    # សង្ខេបលទ្ធផល
    result = (
        f"✅ *ការផ្ញើសារបានបញ្ចប់!*\n\n"
        f"📤 បានផ្ញើ: *{sent}* នាក់\n"
        f"❌ បរាជ័យ: *{failed}* នាក់\n"
        f"👥 សរុប: *{len(workers)}* នាក់"
    )
    if failed_names:
        result += "\n\n⚠️ *មិនអាចផ្ញើទៅ:*\n"
        result += "\n".join(f"• {n}" for n in failed_names[:10])
        if len(failed_names) > 10:
            result += f"\n... និង {len(failed_names)-10} នាក់ទៀត"

    bot.send_message(uid, result, parse_mode="Markdown", reply_markup=main_kb())

# ══════════════════════════════════════════════════════════════════
#  FALLBACK
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: True)
def fallback(message):
    uid = message.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "⛔ អ្នកមិនមានសិត្ធប្រើបូតនេហត។")
        return
    sessions.pop(uid, None)
    bot.send_message(uid, "🏠 មើនូយចម្បង:", reply_markup=main_kb())

# ══════════════════════════════════════════════════════════════════
#  AUTO-NOTIFY: ផ្ញើ notification ជាមួយ button ទៅ admin
#  នៅពេល worker ស្នើច្បាប់ថ្មី (poll រៀងរាល់ 15 វិនាទី)
# ══════════════════════════════════════════════════════════════════

import threading
import time

# រក្សាទុក leave IDs ដែលបានជូនដំណឹងហើយ
_notified_leaves = set()

def _load_already_notified():
    """Load pending leaves that already exist so we don't re-notify on restart."""
    try:
        existing = get_pending_leave_requests()
        for r in existing:
            _notified_leaves.add(r["id"])
    except Exception:
        pass

def notify_admins_new_leaves():
    """Background thread: check for new pending leaves every 15 seconds."""
    _load_already_notified()
    while True:
        try:
            pending = get_pending_leave_requests()
            for r in pending:
                if r["id"] not in _notified_leaves:
                    _notified_leaves.add(r["id"])
                    try:
                        days = (r["end_date"] - r["start_date"]).days + 1
                    except Exception:
                        days = "?"
                    text = (
                        f"🔔 *ការស្នើសុំច្បាប់ថ្មី #{r['id']}*\n\n"
                        f"👤 {r['full_name']} ({r['employee_id']})\n"
                        f"🏢 {r['department']}\n"
                        f"🗂 {LEAVE_TYPE_KH.get(r['leave_type'], r['leave_type'])}\n"
                        f"📆 {r['start_date']} → {r['end_date']} ({days} ថ្ងៃ)\n"
                        f"📝 {r['reason']}"
                    )
                    for admin_id in ADMIN_IDS:
                        try:
                            bot.send_message(
                                admin_id, text,
                                parse_mode="Markdown",
                                reply_markup=leave_action_kb(r["id"])
                            )
                        except Exception:
                            pass
        except Exception:
            pass
        time.sleep(15)


if __name__ == "__main__":
    print("🔐 Admin Bot កំពុងដំណើរការ...")
    # Start notification thread
    t = threading.Thread(target=notify_admins_new_leaves, daemon=True)
    t.start()
    print("🔔 Notification thread started.")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
