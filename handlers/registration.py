# handlers/registration.py - Worker registration flow

from telebot import TeleBot
from database import get_worker_by_telegram_id, register_worker
from keyboards import main_menu_keyboard, cancel_keyboard
from states import REG_NAME, REG_EMP_ID, REG_DEPT, REG_PHONE
from config import ADMIN_IDS

# In-memory session store: {telegram_id: {state: ..., data: {...}}}
sessions = {}


def register_handlers(bot: TeleBot):

    @bot.message_handler(commands=["start"])
    def cmd_start(message):
        uid = message.from_user.id
        worker = get_worker_by_telegram_id(uid)

        if worker:
            # Worker bot — show ONLY worker menu regardless of admin status
            # Admins must use the separate Admin Bot for HR functions
            bot.send_message(
                uid,
                f"👋 សូមស្វាគមន៍មកវិញ *{worker['full_name']}*!\n\nប្រើម៉ឺនុយខាងក្រោម។",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            sessions[uid] = {"state": REG_NAME, "data": {}}
            bot.send_message(
                uid,
                "👋 សូមស្វាគមន៍មក *បូតគ្រប់គ្រងធនធានមនុស្ស*!\n\n"
                "ខ្ញុំជួយគ្រប់គ្រងការស្នើសុំច្បាប់ លិខិតឈឺ និងបញ្ជីប្រាក់ខែ។\n\n"
                "សូមចុះឈ្មោះជាមុនសិន។ បញ្ចូល *ឈ្មោះពេញ* របស់អ្នក៖",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard()
            )

    @bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == REG_NAME)
    def get_name(message):
        uid = message.from_user.id
        if message.text == "❌ បោះបង់":
            sessions.pop(uid, None)
            bot.send_message(uid, "បានបោះបង់ការចុះឈ្មោះ។")
            return

        name = message.text.strip()
        if len(name) < 3:
            bot.send_message(uid, "⚠️ សូមបញ្ចូលឈ្មោះពេញត្រឹមត្រូវ (យ៉ាងហោចណាស់ ៣ តួអក្សរ)។")
            return

        sessions[uid]["data"]["full_name"] = name
        sessions[uid]["state"] = REG_EMP_ID
        bot.send_message(uid, f"ល្អណាស់ *{name}*! សូមបញ្ចូល *លេខសម្គាល់បុគ្គលិក* (ឧ. EMP001):",
                         parse_mode="Markdown")

    @bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == REG_EMP_ID)
    def get_emp_id(message):
        uid = message.from_user.id
        if message.text == "❌ បោះបង់":
            sessions.pop(uid, None)
            bot.send_message(uid, "បានបោះបង់ការចុះឈ្មោះ។")
            return

        emp_id = message.text.strip().upper()
        if len(emp_id) < 3:
            bot.send_message(uid, "⚠️ លេខសម្គាល់បុគ្គលិកខ្លីពេក។ សូមព្យាយាមម្តងទៀត។")
            return

        sessions[uid]["data"]["employee_id"] = emp_id
        sessions[uid]["state"] = REG_DEPT
        bot.send_message(uid, "បញ្ចូល *នាយកដ្ឋាន* របស់អ្នក (ឧ. សំអាត, សំណង់, រដ្ឋបាល):",
                         parse_mode="Markdown")

    @bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == REG_DEPT)
    def get_dept(message):
        uid = message.from_user.id
        if message.text == "❌ បោះបង់":
            sessions.pop(uid, None)
            bot.send_message(uid, "បានបោះបង់ការចុះឈ្មោះ។")
            return

        dept = message.text.strip()
        sessions[uid]["data"]["department"] = dept
        sessions[uid]["state"] = REG_PHONE
        bot.send_message(uid, "បញ្ចូល *លេខទូរស័ព្ទ* របស់អ្នក:", parse_mode="Markdown")

    @bot.message_handler(func=lambda m: sessions.get(m.from_user.id, {}).get("state") == REG_PHONE)
    def get_phone(message):
        uid = message.from_user.id
        if message.text == "❌ បោះបង់":
            sessions.pop(uid, None)
            bot.send_message(uid, "បានបោះបង់ការចុះឈ្មោះ។")
            return

        phone = message.text.strip()
        data = sessions[uid]["data"]

        try:
            register_worker(
                telegram_id=uid,
                full_name=data["full_name"],
                employee_id=data["employee_id"],
                department=data["department"],
                phone=phone
            )
            sessions.pop(uid, None)
            bot.send_message(
                uid,
                f"✅ *ការចុះឈ្មោះបានជោគជ័យ!*\n\n"
                f"👤 ឈ្មោះ: {data['full_name']}\n"
                f"🆔 លេខបុគ្គលិក: {data['employee_id']}\n"
                f"🏢 នាយកដ្ឋាន: {data['department']}\n"
                f"📞 ទូរស័ព្ទ: {phone}\n\n"
                f"អ្នកអាចប្រើម៉ឺនុយខាងក្រោមបានហើយ។",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        except Exception as e:
            if "Duplicate entry" in str(e):
                bot.send_message(uid, "⚠️ លេខបុគ្គលិកនេះបានចុះឈ្មោះរួចហើយ។ សូមទាក់ទងអ្នកគ្រប់គ្រង។")
            else:
                bot.send_message(uid, f"❌ ការចុះឈ្មោះបរាជ័យ: {e}")
            sessions.pop(uid, None)
