"""
Notification service — sends alerts to Admin Bot chat when workers submit leave.
Looks up admin telegram_chat_ids from telegram_sessions by employee_id.
"""
import logging
from bson import ObjectId
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from config import TELEGRAM_ADMIN_TOKEN, ADMIN_EMPLOYEE_IDS
from database.collections import telegram_sessions, employees

logger = logging.getLogger(__name__)


async def get_admin_chat_ids() -> list[str]:
    """Return telegram_chat_ids of all admin employees."""
    chat_ids = []
    for emp_id_str in ADMIN_EMPLOYEE_IDS:
        try:
            sess = await telegram_sessions().find_one(
                {"employee_id": ObjectId(emp_id_str)}
            )
            if sess:
                chat_ids.append(sess["telegram_chat_id"])
        except Exception as e:
            logger.warning(f"Could not find admin session for {emp_id_str}: {e}")
    return chat_ids


async def notify_leave_request(leave_id: str, employee_id,
                                leave_type: str, start_date: str,
                                end_date: str):
    """
    Send leave request notification to all admins via Admin Bot.
    Each message has ✅ Approve / ❌ Reject inline buttons.
    """
    try:
        emp = await employees().find_one({"_id": employee_id})
        emp_name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip() if emp else "Unknown"
        emp_code = emp.get("employee_code", "") if emp else ""
    except Exception:
        emp_name = "Unknown"
        emp_code = ""

    text = (
        f"🔔 *New Leave Request*\n\n"
        f"👤 Worker : {emp_name} ({emp_code})\n"
        f"📋 Type   : {leave_type.capitalize()}\n"
        f"📅 From   : {start_date}\n"
        f"📅 To     : {end_date}\n\n"
        f"Please approve or reject:"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"apl_{leave_id}"),
            InlineKeyboardButton("❌ Reject",  callback_data=f"rjl_{leave_id}"),
        ]
    ])

    admin_chat_ids = await get_admin_chat_ids()
    if not admin_chat_ids:
        logger.warning("No admin chat IDs found — leave notification not sent.")
        return

    bot = Bot(token=TELEGRAM_ADMIN_TOKEN)
    try:
        for chat_id in admin_chat_ids:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
                logger.info(f"Leave notification sent to admin {chat_id}")
            except Exception as e:
                logger.error(f"Failed to notify admin {chat_id}: {e}")
    finally:
        await bot.close()
