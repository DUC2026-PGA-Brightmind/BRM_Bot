"""
Attendance service – check-in / check-out logic.
"""
from datetime import datetime, date
from bson import ObjectId
from database.collections import attendance_logs, employees, telegram_sessions


async def get_employee_by_chat(chat_id: str) -> dict | None:
    session = await telegram_sessions().find_one({"telegram_chat_id": str(chat_id)})
    if not session:
        return None
    return await employees().find_one({"_id": session["employee_id"]})


async def check_in(chat_id: str, location_gps: str = "") -> dict:
    employee = await get_employee_by_chat(chat_id)
    if not employee:
        return {"ok": False, "msg": "❌ You are not registered. Use /register first."}

    today = date.today().isoformat()
    existing = await attendance_logs().find_one(
        {"employee_id": employee["_id"], "work_date": today}
    )
    if existing and existing.get("check_in"):
        return {"ok": False, "msg": "⚠️ You already checked in today."}

    doc = {
        "employee_id": employee["_id"],
        "work_date":   today,
        "check_in":    datetime.utcnow(),
        "check_out":   None,
        "location_gps": location_gps,
        "status":      "present",
    }
    await attendance_logs().insert_one(doc)
    return {"ok": True, "msg": f"✅ Check-in recorded at {doc['check_in'].strftime('%H:%M')} UTC."}


async def check_out(chat_id: str) -> dict:
    employee = await get_employee_by_chat(chat_id)
    if not employee:
        return {"ok": False, "msg": "❌ You are not registered."}

    today = date.today().isoformat()
    log = await attendance_logs().find_one(
        {"employee_id": employee["_id"], "work_date": today, "check_out": None}
    )
    if not log:
        return {"ok": False, "msg": "⚠️ No open check-in found for today."}

    now = datetime.utcnow()
    await attendance_logs().update_one(
        {"_id": log["_id"]},
        {"$set": {"check_out": now}}
    )
    return {"ok": True, "msg": f"✅ Check-out recorded at {now.strftime('%H:%M')} UTC."}


async def my_attendance(chat_id: str) -> str:
    employee = await get_employee_by_chat(chat_id)
    if not employee:
        return "❌ You are not registered."

    cursor = attendance_logs().find(
        {"employee_id": employee["_id"]}
    ).sort("work_date", -1).limit(7)

    logs = await cursor.to_list(length=7)
    if not logs:
        return "📋 No attendance records found."

    lines = ["📋 *Your last 7 attendance records:*"]
    for l in logs:
        cin  = l["check_in"].strftime("%H:%M")  if l.get("check_in")  else "--:--"
        cout = l["check_out"].strftime("%H:%M") if l.get("check_out") else "--:--"
        lines.append(f"• {l['work_date']}  IN:{cin}  OUT:{cout}  [{l['status']}]")
    return "\n".join(lines)
