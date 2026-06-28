"""
User Bot — ភាសាខ្មែរ
Changes:
  - 📦 វត្ថុធាតុដើម  →  📄 Export ច្បាប់  (export approved leaves as PDF)
  - 👤 ប្រវត្តិរូប    →  can view AND edit profile
"""
import logging
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)
from config import TELEGRAM_USER_TOKEN
from database.collections import employees, telegram_sessions
from services.attendance_service import check_in, check_out, my_attendance
from services.leave_service      import submit_leave, my_leaves
from services.employee_service   import get_profile

logger = logging.getLogger(__name__)

ROLES       = ["កម្មករ", "បច្ចេកទេស", "អ្នកគ្រប់គ្រង", "អ្នកបើកបរ", "អ្នកសំអាត", "ផ្សេងៗ"]
LEAVE_TYPES = ["ច្បាប់ប្រចាំឆ្នាំ", "ឈប់សម្រាកឈឺ", "ច្បាប់គ្មានប្រាក់", "បន្ទាន់"]

# user_data keys
K_EDIT_FIELD = "edit_field"   # which profile field is being edited


# ── MongoDB onboarding state ──────────────────────────────────────────────────
async def get_pending(chat_id):
    from database.mongo import get_db
    return await get_db()["pending_registrations"].find_one({"chat_id": chat_id})

async def set_pending(chat_id, data):
    from database.mongo import get_db
    await get_db()["pending_registrations"].update_one(
        {"chat_id": chat_id},
        {"$set": {**data, "chat_id": chat_id, "updated_at": datetime.utcnow()}},
        upsert=True,
    )

async def clear_pending(chat_id):
    from database.mongo import get_db
    await get_db()["pending_registrations"].delete_one({"chat_id": chat_id})

async def get_session(chat_id):
    try:
        return await telegram_sessions().find_one({"telegram_chat_id": str(chat_id)})
    except Exception:
        return None


# ── Keyboards ─────────────────────────────────────────────────────────────────
def main_kb():
    """
    Bottom keyboard:
    - 📍 GPS buttons (Mobile): request_location=True → sends GPS automatically
    - ✅ Text buttons (Desktop fallback): tap sends text, no GPS
    """
    return ReplyKeyboardMarkup([
        [KeyboardButton("📍 ចូលធ្វើការ (GPS)", request_location=True),
         KeyboardButton("📍 ចេញធ្វើការ (GPS)", request_location=True)],
        [KeyboardButton("✅ ចូលធ្វើការ"),
         KeyboardButton("🚪 ចេញពីធ្វើការ")],
        [KeyboardButton("📋 វត្តមាន"),     KeyboardButton("📅 សុំច្បាប់")],
        [KeyboardButton("📄 Export ច្បាប់"), KeyboardButton("👤 ប្រវត្តិរូប")],
        [KeyboardButton("❓ ជំនួយ")],
    ], resize_keyboard=True)

def home_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ ចូលធ្វើការ",        callback_data="ci"),
         InlineKeyboardButton("🚪 ចេញពីធ្វើការ",     callback_data="co")],
        [InlineKeyboardButton("📋 វត្តមាន",            callback_data="att"),
         InlineKeyboardButton("📅 ច្បាប់របស់ខ្ញុំ",   callback_data="myleaves")],
        [InlineKeyboardButton("� Export ច្បាប់",      callback_data="export_leave"),
         InlineKeyboardButton("👤 ប្រវត្តិរូប",       callback_data="profile")],
        [InlineKeyboardButton("📝 សុំច្បាប់ឈប់សម្រាក", callback_data="leave")],
    ])

def back_btn():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 ទំព័រដើម", callback_data="home")]])

def leave_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(t)] for t in LEAVE_TYPES] + [[KeyboardButton("❌ បោះបង់")]],
        resize_keyboard=True, one_time_keyboard=True,
    )

def cancel_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("❌ បោះបង់")]],
        resize_keyboard=True, one_time_keyboard=True,
    )

def role_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(r)] for r in ROLES],
        resize_keyboard=True, one_time_keyboard=True,
    )

def profile_edit_inline(emp_id: str):
    """Inline buttons to edit each profile field."""
    fields = [
        ("first_name",   "ឈ្មោះដំបូង"),
        ("last_name",    "នាមត្រកូល"),
        ("phone_number", "ទូរស័ព្ទ"),
        ("role_title",   "តួនាទី"),
    ]
    btns = [[InlineKeyboardButton(f"✏️ {label}", callback_data=f"pedit|{emp_id}|{field}")]
            for field, label in fields]
    btns.append([InlineKeyboardButton("🏠 ទំព័រដើម", callback_data="home")])
    return InlineKeyboardMarkup(btns)


# ═════════════════════════════════════════════════════════════════════════════
#  /start
# ═════════════════════════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    session = await get_session(chat_id)

    if session:
        try:
            emp  = await employees().find_one({"_id": session["employee_id"]})
            name = emp.get("first_name", "អ្នក") if emp else "អ្នក"
        except Exception:
            name = "អ្នក"
        # Force remove old keyboard first, then send new one
        await update.message.reply_text("🔄", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(
            f"👋 សូមស្វាគមន៍មកវិញ *{name}*!\nជ្រើសសកម្មភាព៖",
            parse_mode="Markdown", reply_markup=main_kb(),
        )
        await update.message.reply_text("📌 *ម៉ឺនុយ​រហ័ស*",
                                        parse_mode="Markdown", reply_markup=home_inline())
        return

    try:
        await clear_pending(chat_id)
        await set_pending(chat_id, {"step": "name"})
    except Exception:
        pass

    await update.message.reply_text(
        "🌟 *សូមស្វាគមន៍មកកាន់ Bright Mind!*\n\n"
        "👤 *ជំហានទី ១/៤* — សូមបញ្ចូល *ឈ្មោះពេញ*៖",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(),
    )


# ═════════════════════════════════════════════════════════════════════════════
#  INLINE CALLBACKS
# ═════════════════════════════════════════════════════════════════════════════
async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    data    = query.data
    chat_id = str(query.message.chat_id)

    if data == "home":
        await query.edit_message_text("📌 *ម៉ឺនុយ​រហ័ស*",
                                      parse_mode="Markdown", reply_markup=home_inline())

    elif data == "ci":
        r = await check_in(chat_id)
        await query.edit_message_text(r["msg"], reply_markup=back_btn())

    elif data == "co":
        r = await check_out(chat_id)
        await query.edit_message_text(r["msg"], reply_markup=back_btn())

    elif data == "att":
        msg = await my_attendance(chat_id)
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_btn())

    elif data == "myleaves":
        msg = await my_leaves(chat_id)
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_btn())

    elif data == "leave":
        await query.message.reply_text("📅 *ជ្រើសរើសប្រភេទច្បាប់*",
                                       parse_mode="Markdown", reply_markup=leave_kb())

    elif data == "profile":
        # Show profile + edit buttons
        sess = await get_session(chat_id)
        if not sess:
            await query.edit_message_text("❌ អ្នកមិនទាន់ចុះឈ្មោះ។", reply_markup=back_btn())
            return
        emp  = await employees().find_one({"_id": sess["employee_id"]})
        if not emp:
            await query.edit_message_text("❌ រកមិនឃើញ។", reply_markup=back_btn())
            return
        eid  = str(emp["_id"])
        name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
        text = (
            f"👤 *ប្រវត្តិរូប*\n\n"
            f"ឈ្មោះ    ៖ {name}\n"
            f"ID        ៖ {emp.get('employee_code','—')}\n"
            f"ទូរស័ព្ទ ៖ {emp.get('phone_number','—')}\n"
            f"តួនាទី  ៖ {emp.get('role_title','—')}\n"
            f"ស្ថានភាព ៖ {emp.get('status','—')}"
        )
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=profile_edit_inline(eid))

    elif data == "export_leave":
        # Export approved leaves as PDF
        sess = await get_session(chat_id)
        if not sess:
            await query.edit_message_text("❌ អ្នកមិនទាន់ចុះឈ្មោះ។", reply_markup=back_btn())
            return
        await query.edit_message_text("⏳ កំពុងបង្កើត PDF ច្បាប់...")
        try:
            from services.pdf_service import generate_leave_pdf
            emp = await employees().find_one({"_id": sess["employee_id"]})
            buf = await generate_leave_pdf(sess["employee_id"])
            name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip() if emp else "worker"
            await query.message.reply_document(
                document=buf,
                filename=f"leave_{name.replace(' ','_')}.pdf",
                caption=f"📄 *ការសុំច្បាប់ដែលអនុម័ត — {name}*",
                parse_mode="Markdown",
            )
            await query.message.reply_text("✅ Export PDF ច្បាប់ជោគជ័យ!",
                                           reply_markup=main_kb())
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {e}", reply_markup=main_kb())

    elif data.startswith("pedit|"):
        # pedit|{emp_id}|{field}
        parts = data[6:].split("|", 1)
        eid   = parts[0]
        field = parts[1] if len(parts) > 1 else ""
        labels = {"first_name":"ឈ្មោះដំបូង", "last_name":"នាមត្រកូល",
                  "phone_number":"ទូរស័ព្ទ",  "role_title":"តួនាទី"}
        ctx.user_data[K_EDIT_FIELD] = field
        ctx.user_data["edit_emp_id"] = eid
        await query.message.reply_text(
            f"✏️ វាយ *{labels.get(field, field)}* ថ្មី៖",
            parse_mode="Markdown",
            reply_markup=cancel_kb(),
        )


# ═════════════════════════════════════════════════════════════════════════════
#  TEXT HANDLER
# ═════════════════════════════════════════════════════════════════════════════
async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text    = update.message.text.strip()
    chat_id = str(update.effective_chat.id)

    # ── Profile edit ──────────────────────────────────────────────────────
    if ctx.user_data.get(K_EDIT_FIELD) and ctx.user_data.get("edit_emp_id"):
        field = ctx.user_data.pop(K_EDIT_FIELD)
        eid   = ctx.user_data.pop("edit_emp_id")
        if text == "❌ បោះបង់":
            await update.message.reply_text("❌ បោះបង់ហើយ។", reply_markup=main_kb())
            return
        from bson import ObjectId
        labels = {"first_name":"ឈ្មោះដំបូង","last_name":"នាមត្រកូល",
                  "phone_number":"ទូរស័ព្ទ","role_title":"តួនាទី"}
        try:
            await employees().update_one({"_id": ObjectId(eid)}, {"$set": {field: text}})
            await update.message.reply_text(
                f"✅ *{labels.get(field,field)}* ត្រូវបានកែទៅ: `{text}`",
                parse_mode="Markdown", reply_markup=main_kb(),
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ {e}", reply_markup=main_kb())
        return

    # ── Onboarding ────────────────────────────────────────────────────────
    try:
        pending = await get_pending(chat_id)
    except Exception:
        pending = None

    if pending:
        step = pending.get("step")
        if step == "name":
            await set_pending(chat_id, {"step": "id", "name": text})
            await update.message.reply_text(
                "🪪 *ជំហានទី ២/៤* — *លេខសម្គាល់* (ឧ. EMP001)៖",
                parse_mode="Markdown")
            return
        if step == "id":
            await set_pending(chat_id, {"step": "phone", "emp_id": text})
            await update.message.reply_text(
                "📱 *ជំហានទី ៣/៤* — *លេខទូរស័ព្ទ*៖",
                parse_mode="Markdown")
            return
        if step == "phone":
            await set_pending(chat_id, {"step": "role", "phone": text})
            await update.message.reply_text(
                "🎭 *ជំហានទី ៤/៤* — ជ្រើសរើស *តួនាទី*៖",
                parse_mode="Markdown", reply_markup=role_kb())
            return
        if step == "role" and text in ROLES:
            name  = pending.get("name","")
            empid = pending.get("emp_id","")
            phone = pending.get("phone","")
            parts = name.strip().split(" ",1)
            try:
                result = await employees().insert_one({
                    "first_name":    parts[0],
                    "last_name":     parts[1] if len(parts)>1 else "",
                    "employee_code": empid,
                    "phone_number":  phone,
                    "role_title":    text,
                    "status":        "active",
                    "hired_at":      datetime.utcnow(),
                })
                await telegram_sessions().insert_one({
                    "telegram_chat_id":   chat_id,
                    "employee_id":        result.inserted_id,
                    "current_state":      "idle",
                    "registration_token": "",
                    "updated_at":         datetime.utcnow(),
                })
                await clear_pending(chat_id)
                await update.message.reply_text(
                    f"✅ *ចុះឈ្មោះបានជោគជ័យ!*\n\n"
                    f"👤 ឈ្មោះ    ៖ {name}\n"
                    f"🪪 ID    ៖ {empid}\n"
                    f"📱 ទូរស័ព្ទ ៖ {phone}\n"
                    f"🎭 តួនាទី  ៖ {text}\n\n"
                    f"🎉 សូមស្វាគមន៍!",
                    parse_mode="Markdown", reply_markup=main_kb())
                await update.message.reply_text("📌 *ម៉ឺនុយ​រហ័ស*",
                                                parse_mode="Markdown", reply_markup=home_inline())
            except Exception as e:
                await update.message.reply_text(f"⚠️ {e}\n\nសាកល្បង /start ម្តងទៀត")
            return
        if step == "role":
            await update.message.reply_text("⚠️ សូមចុច *button* ជ្រើសរើស *តួនាទី*:",
                                            parse_mode="Markdown", reply_markup=role_kb())
            return

    # ── Leave flow ────────────────────────────────────────────────────────
    leave_step = ctx.user_data.get("leave_step")
    if text in LEAVE_TYPES and not leave_step:
        ctx.user_data["leave_type"] = text
        ctx.user_data["leave_step"] = "start"
        await update.message.reply_text(
            f"📅 *{text}*\n\nកាលបរិច្ឆេទ *ចាប់ផ្តើម* (YYYY-MM-DD)៖",
            parse_mode="Markdown", reply_markup=cancel_kb())
        return
    if leave_step == "start":
        ctx.user_data["leave_start"] = text
        ctx.user_data["leave_step"]  = "end"
        await update.message.reply_text("📅 *កាលបរិច្ឆេទបញ្ចប់* (YYYY-MM-DD)៖",
                                        parse_mode="Markdown", reply_markup=cancel_kb())
        return
    if leave_step == "end":
        result = await submit_leave(chat_id,
                                    ctx.user_data.pop("leave_type",""),
                                    ctx.user_data.pop("leave_start",""), text)
        ctx.user_data.pop("leave_step", None)
        await update.message.reply_text(result["msg"], reply_markup=main_kb())
        return

    # ── Cancel ────────────────────────────────────────────────────────────
    if text == "❌ បោះបង់":
        ctx.user_data.clear()
        await update.message.reply_text("❌ បោះបង់ហើយ។", reply_markup=main_kb())
        return

    # ── Bottom keyboard ───────────────────────────────────────────────────
    if text in ("✅ ចូលធ្វើការ", "checkin", "📍 ចូលធ្វើការ (GPS)"):
        r = await check_in(chat_id)
        await update.message.reply_text(r["msg"], reply_markup=main_kb())
    elif text in ("🚪 ចេញពីធ្វើការ", "checkout", "📍 ចេញធ្វើការ (GPS)"):
        r = await check_out(chat_id)
        await update.message.reply_text(r["msg"], reply_markup=main_kb())
    elif text in ("📋 វត្តមាន", "attendance"):
        msg = await my_attendance(chat_id)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_kb())
    elif text in ("📅 សុំច្បាប់", "leave"):
        await update.message.reply_text("📅 *ជ្រើសរើសប្រភេទច្បាប់*",
                                        parse_mode="Markdown", reply_markup=leave_kb())
    elif "export" in text.lower() or "Export" in text or "ច្បាប់" in text and "📄" in text:
        # Handle Export leave — match loosely in case of emoji encoding issues
        await _do_export_leave(update, chat_id)
    elif "profile" in text.lower() or "ប្រវត្តិរូប" in text:
        await _do_show_profile(update, chat_id)
    elif "ជំនួយ" in text or "help" in text.lower():
        await update.message.reply_text(
            "📋 *ពាក្យបញ្ជា*\n\n"
            "/start – ទំព័រដើម\n"
            "/checkin – ចូលធ្វើការ\n"
            "/checkout – ចេញពីធ្វើការ\n"
            "/attendance – ប្រវត្តិវត្តមាន\n"
            "/leave – សុំច្បាប់\n"
            "/myleaves – ច្បាប់របស់ខ្ញុំ\n"
            "/exportleave – Export PDF ច្បាប់\n"
            "/profile – ប្រវត្តិរូប",
            parse_mode="Markdown", reply_markup=main_kb())




# ═════════════════════════════════════════════════════════════════════════════
#  LOCATION HANDLER (GPS check-in / check-out)
# ═════════════════════════════════════════════════════════════════════════════
async def on_location(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handles location message sent via keyboard button."""
    loc     = update.message.location
    chat_id = str(update.effective_chat.id)

    if loc is None:
        await update.message.reply_text("⚠️ រកមិនឃើញ GPS location។", reply_markup=main_kb())
        return

    gps_str = f"{loc.latitude:.6f},{loc.longitude:.6f}"
    maps_url = f"https://maps.google.com/?q={loc.latitude},{loc.longitude}"

    # Check if user already checked in today → treat as check-out
    from database.collections import attendance_logs, telegram_sessions as ts_col
    from datetime import timezone, timedelta
    KH_TZ = timezone(timedelta(hours=7))
    from datetime import datetime
    today = datetime.now(KH_TZ).date().isoformat()

    session = await ts_col().find_one({"telegram_chat_id": chat_id})
    if not session:
        await update.message.reply_text("❌ អ្នកមិនទាន់ចុះឈ្មោះ។ សូម /start ជាមុន។",
                                        reply_markup=main_kb())
        return

    existing = await attendance_logs().find_one({
        "employee_id": session["employee_id"],
        "work_date":   today,
    })

    if existing and existing.get("check_out"):
        await update.message.reply_text(
            "⚠️ អ្នកបានចូល និង ចេញធ្វើការថ្ងៃនេះហើយ។",
            reply_markup=main_kb())
        return

    if existing and existing.get("check_in") and not existing.get("check_out"):
        # → Check-out
        result = await check_out(chat_id)
        msg    = result["msg"]
    else:
        # → Check-in
        result = await check_in(chat_id, location_gps=gps_str)
        msg    = result["msg"]

    await update.message.reply_text(
        f"{msg}\n\n"
        f"📍 GPS: [{loc.latitude:.5f}, {loc.longitude:.5f}]({maps_url})",
        parse_mode="Markdown",
        reply_markup=main_kb(),
    )


# ═════════════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ═════════════════════════════════════════════════════════════════════════════
async def _do_export_leave(update: Update, chat_id: str):
    sess = await get_session(chat_id)
    if not sess:
        await update.message.reply_text("❌ អ្នកមិនទាន់ចុះឈ្មោះ។", reply_markup=main_kb())
        return
    await update.message.reply_text("⏳ កំពុងបង្កើត PDF ច្បាប់...", reply_markup=main_kb())
    try:
        from services.pdf_service import generate_leave_pdf
        emp  = await employees().find_one({"_id": sess["employee_id"]})
        buf  = await generate_leave_pdf(sess["employee_id"])
        name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip() if emp else "worker"
        await update.message.reply_document(
            document=buf,
            filename=f"leave_{name.replace(' ','_')}.pdf",
            caption=f"📄 *ច្បាប់ដែលអនុម័ត — {name}*",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"export_leave error: {e}")
        await update.message.reply_text(f"❌ Error: {e}", reply_markup=main_kb())


async def _do_show_profile(update: Update, chat_id: str):
    sess = await get_session(chat_id)
    if not sess:
        await update.message.reply_text("❌ អ្នកមិនទាន់ចុះឈ្មោះ។", reply_markup=main_kb())
        return
    emp = await employees().find_one({"_id": sess["employee_id"]})
    if not emp:
        await update.message.reply_text("❌ រកមិនឃើញ។", reply_markup=main_kb())
        return
    eid  = str(emp["_id"])
    name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
    await update.message.reply_text(
        f"👤 *ប្រវត្តិរូប*\n\n"
        f"ឈ្មោះ    ៖ {name}\n"
        f"ID        ៖ {emp.get('employee_code','—')}\n"
        f"ទូរស័ព្ទ ៖ {emp.get('phone_number','—')}\n"
        f"តួនាទី  ៖ {emp.get('role_title','—')}\n"
        f"ស្ថានភាព ៖ {emp.get('status','—')}\n\n"
        f"ចុចប៊ូតុងខាងក្រោម *កែ*៖",
        parse_mode="Markdown",
        reply_markup=profile_edit_inline(eid),
    )


# ═════════════════════════════════════════════════════════════════════════════
#  COMMANDS
# ═════════════════════════════════════════════════════════════════════════════
async def cmd_checkin(update, ctx):
    r = await check_in(str(update.effective_chat.id))
    await update.message.reply_text(r["msg"], reply_markup=main_kb())

async def cmd_checkout(update, ctx):
    r = await check_out(str(update.effective_chat.id))
    await update.message.reply_text(r["msg"], reply_markup=main_kb())

async def cmd_attendance(update, ctx):
    msg = await my_attendance(str(update.effective_chat.id))
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_kb())

async def cmd_myleaves(update, ctx):
    msg = await my_leaves(str(update.effective_chat.id))
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_kb())

async def cmd_exportleave(update, ctx):
    await _do_export_leave(update, str(update.effective_chat.id))

async def cmd_profile(update, ctx):
    await _do_show_profile(update, str(update.effective_chat.id))


# ═════════════════════════════════════════════════════════════════════════════
#  BUILD
# ═════════════════════════════════════════════════════════════════════════════
def build_user_app():
    app = ApplicationBuilder().token(TELEGRAM_USER_TOKEN).build()
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("checkin",     cmd_checkin))
    app.add_handler(CommandHandler("checkout",    cmd_checkout))
    app.add_handler(CommandHandler("attendance",  cmd_attendance))
    app.add_handler(CommandHandler("myleaves",    cmd_myleaves))
    app.add_handler(CommandHandler("exportleave", cmd_exportleave))
    app.add_handler(CommandHandler("profile",     cmd_profile))
    app.add_handler(MessageHandler(filters.LOCATION, on_location))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app
