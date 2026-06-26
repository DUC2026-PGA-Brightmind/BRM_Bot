"""
Admin Bot — ភាសាខ្មែរ
"""
import logging, re
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler,
    ContextTypes, filters,
)
from config import TELEGRAM_ADMIN_TOKEN, TELEGRAM_USER_TOKEN, ADMIN_CHAT_IDS
from services.employee_service import create_employee
from services.leave_service    import pending_leaves_for_manager, approve_leave, reject_leave

logger = logging.getLogger(__name__)


# ── Admin Access Guard ────────────────────────────────────────────────────────
async def _check_admin(update: Update) -> bool:
    """Return True if user is allowed. If not, send deny message + notify admins."""
    user    = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None
    uid     = user.id if user else None

    if uid in ADMIN_CHAT_IDS:
        return True

    # Deny access
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() if user else "Unknown"
    username = f"@{user.username}" if user and user.username else "—"

    if update.message:
        await update.message.reply_text(
            "🚫 *គ្មានសិទ្ធិចូល!*\n\nអ្នកមិនមានសិទ្ធិប្រើ Admin Bot នេះទេ។",
            parse_mode="Markdown",
        )
    elif update.callback_query:
        await update.callback_query.answer("🚫 គ្មានសិទ្ធិ!", show_alert=True)

    # Notify all real admins via Admin Bot
    from telegram import Bot
    bot = Bot(token=TELEGRAM_ADMIN_TOKEN)
    alert = (
        f"⚠️ *មានការចូល Admin Bot ដោយគ្មានសិទ្ធិ!*\n\n"
        f"👤 ឈ្មោះ     ៖ {name}\n"
        f"🔖 Username  ៖ {username}\n"
        f"🆔 User ID   ៖ `{uid}`\n"
        f"💬 Chat ID   ៖ `{chat_id}`"
    )
    try:
        for admin_id in ADMIN_CHAT_IDS:
            if admin_id != uid:  # don't echo to the intruder
                try:
                    await bot.send_message(chat_id=admin_id, text=alert,
                                           parse_mode="Markdown")
                except Exception:
                    pass
    finally:
        await bot.close()

    return False

# Conversation states
(
    EMP_FNAME, EMP_LNAME, EMP_EMAIL, EMP_PHONE, EMP_DEPT, EMP_ROLE, EMP_SALARY,
    LEAVE_ID_APPROVE, LEAVE_ID_REJECT,
    BROADCAST_MSG,
    EDIT_FIELD, EDIT_VALUE,
) = range(12)

# user_data keys
KEY_PAYROLL  = "await_payroll_month"
KEY_BCAST    = "await_broadcast"
KEY_BCAST_TG = "bcast_target"
KEY_EDIT_EMP = "edit_emp_id"
KEY_EDIT_F   = "edit_field"


# ── Notify worker on leave decision ──────────────────────────────────────────
async def _notify_worker_leave(leave_id: str, approved: bool):
    from bson import ObjectId
    from telegram import Bot
    from database.collections import leave_requests, telegram_sessions
    try:
        leave = await leave_requests().find_one({"_id": ObjectId(leave_id)})
        if not leave:
            return
        sess = await telegram_sessions().find_one({"employee_id": leave["employee_id"]})
        if not sess:
            return
        if approved:
            msg = (f"✅ *ការសុំច្បាប់ត្រូវបានអនុម័ត!*\n\n"
                   f"📋 {leave.get('leave_type','')}  📅 {leave.get('start_date','')} → {leave.get('end_date','')}")
        else:
            msg = (f"❌ *ការសុំច្បាប់ត្រូវបានបដិសេធ។*\n\n"
                   f"📋 {leave.get('leave_type','')}  📅 {leave.get('start_date','')} → {leave.get('end_date','')}")
        bot = Bot(token=TELEGRAM_USER_TOKEN)
        try:
            await bot.send_message(chat_id=sess["telegram_chat_id"], text=msg, parse_mode="Markdown")
        finally:
            await bot.close()
    except Exception as e:
        logger.error(f"notify_worker_leave: {e}")


# ── Keyboards ─────────────────────────────────────────────────────────────────
def admin_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("👥 បន្ថែមបុគ្គលិក"),     KeyboardButton("📋 ច្បាប់រង់ចាំ")],
        [KeyboardButton("✅ អនុម័តច្បាប់"),        KeyboardButton("❌ បដិសេធច្បាប់")],
        [KeyboardButton("💰 មើលប្រាក់ខែ"),         KeyboardButton("👷 គ្រប់គ្រង Workers")],
        [KeyboardButton("📄 Export PDF"),           KeyboardButton("📢 ជូនដំណឹងទៅ Workers")],
    ], resize_keyboard=True)

def back_btn():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 ទំព័រដើម", callback_data="home")]])

def home_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 បន្ថែមបុគ្គលិក",    callback_data="addemp"),
         InlineKeyboardButton("📋 ច្បាប់រង់ចាំ",      callback_data="pendleaves")],
        [InlineKeyboardButton("💰 មើលប្រាក់ខែ",       callback_data="payroll_view"),
         InlineKeyboardButton("👷 គ្រប់គ្រង Workers", callback_data="manage_workers")],
        [InlineKeyboardButton("📄 Export PDF",         callback_data="export_pdf"),
         InlineKeyboardButton("📢 ជូនដំណឹង Workers",  callback_data="broadcast")],
    ])


# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _check_admin(update):
        return
    ctx.user_data.clear()
    await update.message.reply_text(
        "🛠️ *Bright Mind — ផ្ទាំងគ្រប់គ្រង*\nសូមស្វាគមន៍, Admin!",
        parse_mode="Markdown", reply_markup=admin_kb(),
    )
    await update.message.reply_text("📌 *សកម្មភាព​រហ័ស*", parse_mode="Markdown",
                                    reply_markup=home_inline())

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ បោះបង់ហើយ។", reply_markup=admin_kb())
    return ConversationHandler.END


# ── Payroll View ──────────────────────────────────────────────────────────────
async def _send_payroll_report(reply_fn, month: str):
    from services.payroll_service import get_all_payroll
    workers = await get_all_payroll(month)
    if not workers:
        await reply_fn("📭 មិនមានបុគ្គលិកណាចុះឈ្មោះទេ។")
        return

    lines = [f"💰 *ប្រាក់ខែខែ {month}*  (គោល $300)\n{'─'*32}"]
    btns  = []
    for w in workers:
        emp  = w["emp"]
        name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
        code = emp.get("employee_code", "—")
        pen  = f"  ⚠️ ពិន័យ: -${w['deduction']:.2f} ({w['penalty_count']}×$5)" if w["deduction"] > 0 else ""
        lines.append(
            f"\n👤 *{name}* ({code})\n"
            f"   ✅ វត្តមាន  : {w['present']} ថ្ងៃ\n"
            f"   ⏰ យឺត     : {w['late']} ដង\n"
            f"   🌗 កន្លះថ្ងៃ: {w['half_day']} ថ្ងៃ\n"
            f"   ❌ អវត្តមាន: {w['absent']} ដង"
            f"{pen}\n"
            f"   💵 សុទ្ធ   : *${w['net_pay']:.2f}*"
        )
        cid = w.get("telegram_chat_id","")
        if cid:
            btns.append([InlineKeyboardButton(
                f"📤 ផ្ញើ Payslip → {name}",
                callback_data=f"spay_{cid}|{month}"
            )])
    btns.append([InlineKeyboardButton(
        "📢 ផ្ញើ Payslip ទៅ Workers ទាំងអស់",
        callback_data=f"spay_all|{month}"
    )])
    btns.append([InlineKeyboardButton("🏠 ទំព័រដើម", callback_data="home")])
    await reply_fn("\n".join(lines), parse_mode="Markdown",
                   reply_markup=InlineKeyboardMarkup(btns))


# ── Worker Manager ────────────────────────────────────────────────────────────
async def _send_worker_list(reply_fn):
    from database.collections import telegram_sessions, employees
    sessions = await telegram_sessions().find({}).to_list(length=200)
    if not sessions:
        await reply_fn("📭 មិនមានបុគ្គលិកណាចុះឈ្មោះទេ។")
        return
    lines = [f"👷 *Workers ចុះឈ្មោះ ({len(sessions)} នាក់)*\n{'─'*30}"]
    btns  = []
    for s in sessions:
        try:
            emp  = await employees().find_one({"_id": s["employee_id"]})
            if not emp:
                continue
            name  = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
            code  = emp.get("employee_code","—")
            phone = emp.get("phone_number","—")
            role  = emp.get("role_title","—")
            eid   = str(emp["_id"])
            lines.append(f"• *{name}* | {code} | {role} | {phone}")
            btns.append([
                InlineKeyboardButton(f"✏️ កែ — {name}", callback_data=f"edit_w|{eid}"),
                InlineKeyboardButton(f"🗑 លុប",          callback_data=f"del_w|{eid}"),
            ])
        except Exception:
            continue
    btns.append([InlineKeyboardButton("🏠 ទំព័រដើម", callback_data="home")])
    await reply_fn("\n".join(lines), parse_mode="Markdown",
                   reply_markup=InlineKeyboardMarkup(btns))


# ── Inline callback ───────────────────────────────────────────────────────────
async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _check_admin(update):
        return
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "home":
        ctx.user_data.clear()
        await query.edit_message_text("📌 *សកម្មភាព​រហ័ស*", parse_mode="Markdown",
                                      reply_markup=home_inline())

    elif data == "export_pdf":
        # Show PDF export options
        await query.edit_message_text(
            "📄 *Export PDF*\n\nជ្រើសរើសប្រភេទ Report៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👷 Workers ទាំងអស់",      callback_data="pdf_workers")],
                [InlineKeyboardButton("💰 ប្រាក់ខែ (ខែនេះ)",     callback_data="pdf_payroll")],
                [InlineKeyboardButton("📋 វត្តមាន (ខែនេះ)",      callback_data="pdf_attendance")],
                [InlineKeyboardButton("🏠 ទំព័រដើម",              callback_data="home")],
            ])
        )

    elif data == "pdf_workers":
        await query.edit_message_text("⏳ កំពុងបង្កើត PDF Workers...")
        try:
            from services.pdf_service import generate_workers_pdf
            buf = await generate_workers_pdf()
            await query.message.reply_document(
                document=buf,
                filename="workers_report.pdf",
                caption="👷 *Workers Report*",
                parse_mode="Markdown",
            )
            await query.message.reply_text("✅ PDF Workers ត្រូវបានបង្កើត!", reply_markup=admin_kb())
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {e}", reply_markup=admin_kb())

    elif data == "pdf_payroll":
        ctx.user_data["pdf_type"] = "payroll"
        ctx.user_data["await_pdf_month"] = True
        month = datetime.utcnow().strftime("%Y-%m")
        await query.message.reply_text(
            f"💰 *Export Payroll PDF*\n\nវាយ *ខែ* (YYYY-MM)\nឧទាហរណ៍: `{month}`",
            parse_mode="Markdown",
        )

    elif data == "pdf_attendance":
        ctx.user_data["pdf_type"] = "attendance"
        ctx.user_data["await_pdf_month"] = True
        month = datetime.utcnow().strftime("%Y-%m")
        await query.message.reply_text(
            f"📋 *Export Attendance PDF*\n\nវាយ *ខែ* (YYYY-MM)\nឧទាហរណ៍: `{month}`",
            parse_mode="Markdown",
        )

    elif data == "payroll_view":
        ctx.user_data[KEY_PAYROLL] = True
        month = datetime.utcnow().strftime("%Y-%m")
        await query.message.reply_text(
            f"💰 *មើលប្រាក់ខែ*\n\nសូមវាយ *ខែ* (YYYY-MM)\nឧទាហរណ៍: `{month}`",
            parse_mode="Markdown",
        )

    elif data == "manage_workers":
        async def rf(t, **kw): await query.message.reply_text(t, **kw)
        await _send_worker_list(rf)

    elif data == "pendleaves":
        leaves = await pending_leaves_for_manager()
        if not leaves:
            await query.edit_message_text("✅ មិនមានច្បាប់រង់ចាំ។", reply_markup=back_btn())
            return
        from database.collections import employees
        lines, btns = ["📋 *ច្បាប់រង់ចាំ*\n"], []
        for l in leaves:
            lid = str(l["_id"])
            try:
                emp  = await employees().find_one({"_id": l["employee_id"]})
                name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip() if emp else "?"
            except Exception:
                name = "?"
            lines.append(f"👤 *{name}*  {l.get('leave_type','?')}  {l.get('start_date','')} → {l.get('end_date','')}\n")
            btns.append([
                InlineKeyboardButton("✅ អនុម័ត", callback_data=f"apl|{lid}"),
                InlineKeyboardButton("❌ បដិសេធ", callback_data=f"rjl|{lid}"),
            ])
        btns.append([InlineKeyboardButton("🏠 ទំព័រដើម", callback_data="home")])
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("apl|"):
        lid = data[4:]
        await approve_leave(lid, manager_emp_id=None)
        await _notify_worker_leave(lid, approved=True)
        await query.edit_message_text("✅ អនុម័ត + ជូនដំណឹងហើយ។", reply_markup=back_btn())

    elif data.startswith("rjl|"):
        lid = data[4:]
        await reject_leave(lid, manager_emp_id=None)
        await _notify_worker_leave(lid, approved=False)
        await query.edit_message_text("❌ បដិសេធ + ជូនដំណឹងហើយ។", reply_markup=back_btn())

    elif data.startswith("spay_all|"):
        month = data[9:]
        from services.payroll_service import get_all_payroll
        from telegram import Bot
        workers = await get_all_payroll(month)
        bot = Bot(token=TELEGRAM_USER_TOKEN)
        sent = failed = 0
        try:
            for w in workers:
                cid  = w.get("telegram_chat_id","")
                emp  = w["emp"]
                name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
                if not cid:
                    continue
                pen  = f"\n   ⚠️ ពិន័យ    : -${w['deduction']:.2f}" if w["deduction"] > 0 else ""
                msg  = (f"💰 *Payslip ខែ {month}*\n\n"
                        f"👤 ឈ្មោះ      ៖ {name}\n"
                        f"✅ វត្តមាន    ៖ {w['present']} ថ្ងៃ\n"
                        f"⏰ យឺត        ៖ {w['late']} ដង\n"
                        f"❌ អវត្តមាន  ៖ {w['absent']} ដង{pen}\n"
                        f"💵 ប្រាក់ខែ   ៖ *${w['net_pay']:.2f}*")
                try:
                    await bot.send_message(chat_id=cid, text=msg, parse_mode="Markdown")
                    sent += 1
                except Exception:
                    failed += 1
        finally:
            await bot.close()
        await query.edit_message_text(
            f"✅ ផ្ញើទៅ *{sent}* នាក់  ❌ បរាជ័យ *{failed}* នាក់",
            parse_mode="Markdown", reply_markup=back_btn())

    elif data.startswith("spay_"):
        # spay_{chat_id}|{month}
        rest  = data[5:]
        parts = rest.split("|", 1)
        cid   = parts[0]
        month = parts[1] if len(parts) > 1 else ""
        from services.payroll_service import get_all_payroll
        from telegram import Bot
        workers = await get_all_payroll(month)
        w = next((x for x in workers if x.get("telegram_chat_id") == cid), None)
        if not w:
            await query.edit_message_text("⚠️ រកមិនឃើញ。", reply_markup=back_btn())
            return
        emp  = w["emp"]
        name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
        pen  = f"\n   ⚠️ ពិន័យ    : -${w['deduction']:.2f}" if w["deduction"] > 0 else ""
        msg  = (f"💰 *Payslip ខែ {month}*\n\n"
                f"👤 ឈ្មោះ      ៖ {name}\n"
                f"✅ វត្តមាន    ៖ {w['present']} ថ្ងៃ\n"
                f"⏰ យឺត        ៖ {w['late']} ដង\n"
                f"❌ អវត្តមាន  ៖ {w['absent']} ដង{pen}\n"
                f"💵 ប្រាក់ខែ   ៖ *${w['net_pay']:.2f}*")
        bot = Bot(token=TELEGRAM_USER_TOKEN)
        try:
            await bot.send_message(chat_id=cid, text=msg, parse_mode="Markdown")
            await query.edit_message_text(f"✅ ផ្ញើ Payslip ទៅ {name} ហើយ។", reply_markup=back_btn())
        except Exception as e:
            await query.edit_message_text(f"❌ {e}", reply_markup=back_btn())
        finally:
            await bot.close()

    elif data.startswith("edit_w|"):
        from bson import ObjectId
        from database.collections import employees
        eid = data[7:]
        emp = await employees().find_one({"_id": ObjectId(eid)})
        if not emp:
            await query.edit_message_text("⚠️ រកមិនឃើញ。", reply_markup=back_btn())
            return
        name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
        fields = [
            ("first_name","ឈ្មោះដំបូង"), ("last_name","នាមត្រកូល"),
            ("phone_number","ទូរស័ព្ទ"),  ("employee_code","លេខ ID"),
            ("role_title","តួនាទី"),
        ]
        btns = [[InlineKeyboardButton(f"✏️ {label}", callback_data=f"ef|{eid}|{field}")]
                for field, label in fields]
        btns.append([InlineKeyboardButton("🔙 ត្រឡប់", callback_data="manage_workers")])
        await query.edit_message_text(
            f"✏️ *កែព័ត៌មាន — {name}*\n\nជ្រើសរើសចំណុចដែលចង់កែ៖",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("ef|"):
        parts = data[3:].split("|", 1)
        eid   = parts[0]
        field = parts[1] if len(parts) > 1 else ""
        ctx.user_data[KEY_EDIT_EMP] = eid
        ctx.user_data[KEY_EDIT_F]   = field
        labels = {"first_name":"ឈ្មោះដំបូង","last_name":"នាមត្រកូល",
                  "phone_number":"ទូរស័ព្ទ","employee_code":"លេខ ID","role_title":"តួនាទី"}
        await query.message.reply_text(
            f"✏️ វាយ *{labels.get(field, field)}* ថ្មី៖",
            parse_mode="Markdown")

    elif data.startswith("del_w|"):
        from bson import ObjectId
        from database.collections import telegram_sessions, employees
        eid = data[6:]
        try:
            oid = ObjectId(eid)
            await telegram_sessions().delete_one({"employee_id": oid})
            await employees().update_one({"_id": oid}, {"$set": {"status": "inactive"}})
            await query.edit_message_text("🗑 Worker ត្រូវបានលុប។", reply_markup=back_btn())
        except Exception as e:
            await query.edit_message_text(f"⚠️ {e}", reply_markup=back_btn())

    elif data == "broadcast":
        ctx.user_data[KEY_BCAST]    = True
        ctx.user_data[KEY_BCAST_TG] = "all"
        await query.message.reply_text("📢 *ជូនដំណឹងទៅ Workers ទាំងអស់*\n\nវាយ *សារ*៖",
                                       parse_mode="Markdown")


# ── Text handler (ALL text goes here) ─────────────────────────────────────────
async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _check_admin(update):
        return
    text = update.message.text.strip()

    # ── 0. PDF month input ────────────────────────────────────────────────
    if ctx.user_data.get("await_pdf_month"):
        if re.match(r"^\d{4}-\d{2}$", text):
            ctx.user_data.pop("await_pdf_month")
            pdf_type = ctx.user_data.pop("pdf_type", "payroll")
            await update.message.reply_text("⏳ កំពុងបង្កើត PDF...")
            try:
                if pdf_type == "payroll":
                    from services.pdf_service import generate_payroll_pdf
                    buf = await generate_payroll_pdf(text)
                    fname = f"payroll_{text}.pdf"
                    cap   = f"💰 *Payroll Report — {text}*"
                else:
                    from services.pdf_service import generate_attendance_pdf
                    buf = await generate_attendance_pdf(text)
                    fname = f"attendance_{text}.pdf"
                    cap   = f"📋 *Attendance Report — {text}*"
                await update.message.reply_document(
                    document=buf, filename=fname,
                    caption=cap, parse_mode="Markdown",
                )
                await update.message.reply_text("✅ PDF បង្កើតបានជោគជ័យ!", reply_markup=admin_kb())
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {e}", reply_markup=admin_kb())
        else:
            await update.message.reply_text(
                f"⚠️ YYYY-MM ឧ. `{datetime.utcnow().strftime('%Y-%m')}`",
                parse_mode="Markdown")
        return

    # ── 1. Payroll month input ────────────────────────────────────────────
    if ctx.user_data.get(KEY_PAYROLL):
        if re.match(r"^\d{4}-\d{2}$", text):
            ctx.user_data.pop(KEY_PAYROLL)
            async def rf(t, **kw): await update.message.reply_text(t, **kw)
            await _send_payroll_report(rf, text)
        else:
            await update.message.reply_text(
                f"⚠️ សូមវាយទំរង់ YYYY-MM  ឧ. `{datetime.utcnow().strftime('%Y-%m')}`",
                parse_mode="Markdown")
        return

    # ── 2. Broadcast message input ────────────────────────────────────────
    if ctx.user_data.get(KEY_BCAST):
        ctx.user_data.pop(KEY_BCAST)
        target = ctx.user_data.pop(KEY_BCAST_TG, "all")
        from telegram import Bot
        from database.collections import telegram_sessions
        bot = Bot(token=TELEGRAM_USER_TOKEN)
        sent = failed = 0
        try:
            if target == "all":
                sessions = await telegram_sessions().find({}).to_list(length=500)
                targets  = [s["telegram_chat_id"] for s in sessions]
            else:
                targets  = [target]
            for cid in targets:
                try:
                    await bot.send_message(chat_id=cid,
                        text=f"📢 *សារពីអ្នកគ្រប់គ្រង*\n\n{text}",
                        parse_mode="Markdown")
                    sent += 1
                except Exception:
                    failed += 1
        finally:
            await bot.close()
        await update.message.reply_text(
            f"✅ ផ្ញើទៅ *{sent}* នាក់  ❌ បរាជ័យ *{failed}* នាក់",
            parse_mode="Markdown", reply_markup=admin_kb())
        return

    # ── 3. Edit worker field input ────────────────────────────────────────
    if ctx.user_data.get(KEY_EDIT_EMP) and ctx.user_data.get(KEY_EDIT_F):
        from bson import ObjectId
        from database.collections import employees
        eid   = ctx.user_data.pop(KEY_EDIT_EMP)
        field = ctx.user_data.pop(KEY_EDIT_F)
        try:
            await employees().update_one({"_id": ObjectId(eid)}, {"$set": {field: text}})
            labels = {"first_name":"ឈ្មោះដំបូង","last_name":"នាមត្រកូល",
                      "phone_number":"ទូរស័ព្ទ","employee_code":"លេខ ID","role_title":"តួនាទី"}
            await update.message.reply_text(
                f"✅ *{labels.get(field,field)}* ត្រូវបានកែទៅ: `{text}`",
                parse_mode="Markdown", reply_markup=admin_kb())
        except Exception as e:
            await update.message.reply_text(f"⚠️ {e}", reply_markup=admin_kb())
        return

    # ── 4. Bottom keyboard routing ────────────────────────────────────────
    if text == "📄 Export PDF":
        await update.message.reply_text(
            "📄 *Export PDF*\n\nជ្រើសរើស Report៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👷 Workers ទាំងអស់",   callback_data="pdf_workers")],
                [InlineKeyboardButton("💰 ប្រាក់ខែ",          callback_data="pdf_payroll")],
                [InlineKeyboardButton("📋 វត្តមាន",           callback_data="pdf_attendance")],
            ])
        )
        return

    if text == "💰 មើលប្រាក់ខែ":
        ctx.user_data[KEY_PAYROLL] = True
        month = datetime.utcnow().strftime("%Y-%m")
        await update.message.reply_text(
            f"💰 *មើលប្រាក់ខែ*\n\nសូមវាយ *ខែ* (YYYY-MM)\nឧទាហរណ៍: `{month}`",
            parse_mode="Markdown")
        return

    if text == "👷 គ្រប់គ្រង Workers":
        async def rf(t, **kw): await update.message.reply_text(t, **kw)
        await _send_worker_list(rf)
        return

    if text == "📢 ជូនដំណឹងទៅ Workers":
        ctx.user_data[KEY_BCAST]    = True
        ctx.user_data[KEY_BCAST_TG] = "all"
        await update.message.reply_text(
            "📢 *ជូនដំណឹងទៅ Workers ទាំងអស់*\n\nវាយ *សារ*៖",
            parse_mode="Markdown")
        return

    if text == "📋 ច្បាប់រង់ចាំ":
        await cmd_pending_leaves(update, ctx)
        return

    if text == "✅ អនុម័តច្បាប់":
        await update.message.reply_text("✅ វាយ *Leave ID* ដើម្បីអនុម័ត៖",
                                        parse_mode="Markdown")
        ctx.user_data["await_leave_approve"] = True
        return

    if text == "❌ បដិសេធច្បាប់":
        await update.message.reply_text("❌ វាយ *Leave ID* ដើម្បីបដិសេធ៖",
                                        parse_mode="Markdown")
        ctx.user_data["await_leave_reject"] = True
        return

    if ctx.user_data.get("await_leave_approve"):
        ctx.user_data.pop("await_leave_approve")
        await approve_leave(text, manager_emp_id=None)
        await _notify_worker_leave(text, approved=True)
        await update.message.reply_text("✅ អនុម័ត + ជូនដំណឹងហើយ។", reply_markup=admin_kb())
        return

    if ctx.user_data.get("await_leave_reject"):
        ctx.user_data.pop("await_leave_reject")
        await reject_leave(text, manager_emp_id=None)
        await _notify_worker_leave(text, approved=False)
        await update.message.reply_text("❌ បដិសេធ + ជូនដំណឹងហើយ។", reply_markup=admin_kb())
        return

    if text == "👥 បន្ថែមបុគ្គលិក":
        await cmd_add_employee(update, ctx)
        return


# ── Pending leaves command ────────────────────────────────────────────────────
async def cmd_pending_leaves(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    leaves = await pending_leaves_for_manager()
    if not leaves:
        await update.message.reply_text("✅ មិនមានច្បាប់រង់ចាំ។", reply_markup=admin_kb())
        return
    from database.collections import employees
    lines, btns = ["📋 *ច្បាប់រង់ចាំ*\n"], []
    for l in leaves:
        lid = str(l["_id"])
        try:
            emp  = await employees().find_one({"_id": l["employee_id"]})
            name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip() if emp else "?"
        except Exception:
            name = "?"
        lines.append(f"👤 *{name}*  {l.get('leave_type','?')}  {l.get('start_date','')} → {l.get('end_date','')}\n")
        btns.append([
            InlineKeyboardButton("✅ អនុម័ត", callback_data=f"apl|{lid}"),
            InlineKeyboardButton("❌ បដិសេធ", callback_data=f"rjl|{lid}"),
        ])
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(btns))


# ── Add Employee (ConversationHandler) ────────────────────────────────────────
async def cmd_add_employee(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("👤 *ឈ្មោះ​ដំបូង?*", parse_mode="Markdown")
    return EMP_FNAME

async def emp_fname(u, c):
    c.user_data["ef"] = u.message.text.strip()
    await u.message.reply_text("👤 *នាមត្រកូល?*", parse_mode="Markdown")
    return EMP_LNAME

async def emp_lname(u, c):
    c.user_data["el"] = u.message.text.strip()
    await u.message.reply_text("📧 *អ៊ីមែល?*", parse_mode="Markdown")
    return EMP_EMAIL

async def emp_email(u, c):
    c.user_data["ee"] = u.message.text.strip()
    await u.message.reply_text("📱 *ទូរស័ព្ទ?*", parse_mode="Markdown")
    return EMP_PHONE

async def emp_phone(u, c):
    c.user_data["ep"] = u.message.text.strip()
    await u.message.reply_text("🏢 *Department ID?*", parse_mode="Markdown")
    return EMP_DEPT

async def emp_dept(u, c):
    c.user_data["ed"] = u.message.text.strip()
    await u.message.reply_text("🎭 *Role?*", parse_mode="Markdown")
    return EMP_ROLE

async def emp_role(u, c):
    c.user_data["er"] = u.message.text.strip()
    await u.message.reply_text("💰 *ប្រាក់ខែ?*", parse_mode="Markdown")
    return EMP_SALARY

async def emp_salary(u, c):
    try:
        sal = float(u.message.text.strip())
    except ValueError:
        await u.message.reply_text("⚠️ សូមបញ្ចូលលេខ。")
        return EMP_SALARY
    r = await create_employee(
        first_name=c.user_data["ef"], last_name=c.user_data["el"],
        email=c.user_data["ee"],      phone=c.user_data["ep"],
        department_id=c.user_data["ed"], role_id=c.user_data["er"],
        base_salary=sal,
    )
    await u.message.reply_text(
        f"{r['msg']}\n🔑 Token: `{r.get('token','')}`",
        parse_mode="Markdown", reply_markup=admin_kb())
    return ConversationHandler.END


# ── App builder ───────────────────────────────────────────────────────────────
def build_admin_app():
    app = ApplicationBuilder().token(TELEGRAM_ADMIN_TOKEN).build()

    emp_conv = ConversationHandler(
        entry_points=[CommandHandler("addemployee", cmd_add_employee),
                      MessageHandler(filters.Regex("^👥 បន្ថែមបុគ្គលិក$"), cmd_add_employee)],
        states={
            EMP_FNAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, emp_fname)],
            EMP_LNAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, emp_lname)],
            EMP_EMAIL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, emp_email)],
            EMP_PHONE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, emp_phone)],
            EMP_DEPT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, emp_dept)],
            EMP_ROLE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, emp_role)],
            EMP_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, emp_salary)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start",         cmd_start))
    app.add_handler(CommandHandler("pendingleaves", cmd_pending_leaves))
    app.add_handler(emp_conv)
    app.add_handler(CallbackQueryHandler(on_callback))
    # General text LAST
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app
