"""
Material / inventory log service.
"""
from datetime import datetime
from database.collections import material_logs, telegram_sessions, employees


async def get_employee_by_chat(chat_id: str) -> dict | None:
    session = await telegram_sessions().find_one({"telegram_chat_id": str(chat_id)})
    if not session:
        return None
    return await employees().find_one({"_id": session["employee_id"]})


async def log_material(chat_id: str, material_name: str,
                       quantity: float, unit: str,
                       transaction_type: str) -> dict:
    employee = await get_employee_by_chat(chat_id)
    if not employee:
        return {"ok": False, "msg": "❌ You are not registered."}

    doc = {
        "employee_id":        employee["_id"],
        "material_name":      material_name,
        "quantity_adjusted":  quantity,
        "unit":               unit,
        "transaction_type":   transaction_type,
        "logged_at":          datetime.utcnow(),
    }
    await material_logs().insert_one(doc)
    return {"ok": True, "msg": f"✅ Material log saved: {quantity} {unit} of {material_name} [{transaction_type}]."}


async def recent_materials(chat_id: str) -> str:
    employee = await get_employee_by_chat(chat_id)
    if not employee:
        return "❌ You are not registered."

    cursor = material_logs().find(
        {"employee_id": employee["_id"]}
    ).sort("logged_at", -1).limit(5)

    logs = await cursor.to_list(length=5)
    if not logs:
        return "📦 No material logs found."

    lines = ["📦 *Recent material logs:*"]
    for l in logs:
        ts = l["logged_at"].strftime("%Y-%m-%d %H:%M")
        lines.append(
            f"• {l['material_name']}  {l['quantity_adjusted']} {l['unit']}  [{l['transaction_type']}]  {ts}"
        )
    return "\n".join(lines)
