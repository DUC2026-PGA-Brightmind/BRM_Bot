# keyboards.py - Telegram inline and reply keyboards (Khmer)

from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def main_menu_keyboard():
    """ម៉ឺនុយសម្រាប់បុគ្គលិក"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("🕐 ចូលធ្វើការ"),
        KeyboardButton("🕔 ចេញធ្វើការ"),
        KeyboardButton("📋 ស្នើសុំ & លិខិត"),   # ← merged button
        KeyboardButton("💰 បញ្ជីប្រាក់ខែខ្ញុំ"),
        KeyboardButton("📋 ស្ថានភាពច្បាប់ខ្ញុំ"),
        KeyboardButton("📆 វត្តមានខ្ញុំ"),
        KeyboardButton("ℹ️ ប្រវត្តិរូបខ្ញុំ")
    )
    return kb


def request_submenu_keyboard():
    """Submenu: ស្នើសុំច្បាប់ ឬ បញ្ជូនលិខិតឈឺ"""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📅 ស្នើសុំច្បាប់", callback_data="sub_leave"),
        InlineKeyboardButton("🤒 បញ្ជូនលិខិតឈឺ", callback_data="sub_sick"),
        InlineKeyboardButton("❌ បោះបង់", callback_data="sub_cancel")
    )
    return kb


def admin_menu_keyboard():
    """ម៉ឺនុយសម្រាប់អ្នកគ្រប់គ្រង"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("📋 ច្បាប់កំពុងរង់ចាំ"),
        KeyboardButton("🤒 លិខិតឈឺកំពុងរង់ចាំ"),
        KeyboardButton("💰 បញ្ជូនបញ្ជីប្រាក់ខែ"),
        KeyboardButton("👥 បុគ្គលិកទាំងអស់"),
        KeyboardButton("📢 សារជូនដំណឹង"),
        KeyboardButton("🔙 ម៉ឺនុយបុគ្គលិក")
    )
    return kb


def leave_type_keyboard():
    """ប្រភេទច្បាប់"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🌴 ច្បាប់ប្រចាំឆ្នាំ", callback_data="ltype_annual"),
        InlineKeyboardButton("🤒 ច្បាប់ឈឺ",         callback_data="ltype_sick"),
        InlineKeyboardButton("🚨 ច្បាប់បន្ទាន់",     callback_data="ltype_emergency"),
        InlineKeyboardButton("💸 ច្បាប់គ្មានប្រាក់ខែ", callback_data="ltype_unpaid")
    )
    return kb


def leave_action_keyboard(leave_id):
    """ប៊ូតុងអនុម័ត/បដិសេធ"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ អនុម័ត", callback_data=f"leave_approve_{leave_id}"),
        InlineKeyboardButton("❌ បដិសេធ", callback_data=f"leave_reject_{leave_id}")
    )
    return kb


def cancel_keyboard():
    """ប៊ូតុងបោះបង់"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ បោះបង់"))
    return kb


def confirm_keyboard():
    """ប៊ូតុងបញ្ជាក់/បោះបង់"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("✅ បញ្ជាក់"), KeyboardButton("❌ បោះបង់"))
    return kb
