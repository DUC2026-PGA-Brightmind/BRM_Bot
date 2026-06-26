"""
Employee registration & profile service.
"""
import secrets
from datetime import datetime
from database.collections import employees, telegram_sessions, roles, departments


async def register_employee(chat_id: str, token: str) -> dict:
    """
    Link a Telegram chat_id to an employee via a pre-issued registration token.
    """
    emp = await employees().find_one({"registration_token": token})
    if not emp:
        # Token not on employee; check pending session
        session = await telegram_sessions().find_one({"registration_token": token})
        if session:
            emp = await employees().find_one({"_id": session.get("employee_id")})

    if not emp:
        return {"ok": False, "msg": "❌ Invalid registration token."}

    existing = await telegram_sessions().find_one({"telegram_chat_id": str(chat_id)})
    if existing:
        return {"ok": False, "msg": "⚠️ This Telegram account is already linked."}

    doc = {
        "telegram_chat_id":   str(chat_id),
        "employee_id":        emp["_id"],
        "current_state":      "idle",
        "registration_token": token,
        "updated_at":         datetime.utcnow(),
    }
    await telegram_sessions().insert_one(doc)
    name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
    return {"ok": True, "msg": f"✅ Welcome, {name}! Your account is now linked."}


async def get_profile(chat_id: str) -> str:
    session = await telegram_sessions().find_one({"telegram_chat_id": str(chat_id)})
    if not session:
        return "❌ You are not registered. Use /register <token> to link your account."

    emp = await employees().find_one({"_id": session["employee_id"]})
    if not emp:
        return "❌ Employee record not found."

    role = await roles().find_one({"_id": emp.get("role_id")})
    dept = await departments().find_one({"_id": emp.get("department_id")})

    return (
        f"👤 *Profile*\n"
        f"Name   : {emp.get('first_name','')} {emp.get('last_name','')}\n"
        f"Email  : {emp.get('email','—')}\n"
        f"Phone  : {emp.get('phone_number','—')}\n"
        f"Role   : {role['title'] if role else '—'}\n"
        f"Dept   : {dept['name'] if dept else '—'}\n"
        f"Status : {emp.get('status','—')}\n"
        f"Hired  : {emp.get('hired_at','—')}"
    )


async def create_employee(first_name: str, last_name: str, email: str,
                           phone: str, department_id, role_id,
                           base_salary: float) -> dict:
    token = secrets.token_hex(8)
    doc = {
        "first_name":         first_name,
        "last_name":          last_name,
        "email":              email,
        "phone_number":       phone,
        "department_id":      department_id,
        "role_id":            role_id,
        "base_salary":        base_salary,
        "status":             "active",
        "hired_at":           datetime.utcnow(),
        "registration_token": token,
    }
    result = await employees().insert_one(doc)
    return {
        "ok":    True,
        "id":    str(result.inserted_id),
        "token": token,
        "msg":   f"✅ Employee created. Registration token: {token}",
    }
