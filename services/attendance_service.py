"""
Attendance service — ម៉ោងកម្ពុជា (UTC+7)
"""
from datetime import datetime, date, timezone, timedelta
from bson import ObjectId
from database.collections import attendance_logs, employees, telegram_sessions

# ── Cambodia timezone UTC+7 ───────────────────────────────────────────────────
KH_TZ    = timezone(timedelta(hours=7))

def now_kh() -> datetime:
    """Return current datetime in Cambodia time (UTC+7)."""
    return datetime.now(KH_TZ)

def today_kh() -> str:
    """Return today's date string in Cambodia time."""
    return now_kh().date().isoformat()

def fmt_kh(dt: datetime) -> str:
    """Format datetime to Cambodia time HH:MM."""
    if dt is None:
        return "--:--"
    # If naive (UTC stored in DB), add UTC then convert
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KH_TZ).strftime("%H:%M")


# ── Helpers ───────────────────────────────────────────────────────────────────
async def get_employee_by_chat(chat_id: str) -> dict | None:
    session = await telegram_sessions().find_one({"telegram_chat_id": str(chat_id)})
    if not session:
        return None
    return await employees().find_one({"_id": session["employee_id"]})


# ═════════════════════════════════════════════════════════════════════════════
async def check_in(chat_id: str, location_gps: str = "") -> dict:
    employee = await get_employee_by_chat(chat_id)
    if not employee:
        return {"ok": False, "msg": "❌ អ្នកមិនទាន់ចុះឈ្មោះ។ សូម /start ជាមុន។"}

    today    = today_kh()
    existing = await attendance_logs().find_one(
        {"employee_id": employee["_id"], "work_date": today}
    )
    if existing and existing.get("check_in"):
        return {"ok": False, "msg": "⚠️ អ្នកបានចូលធ្វើការថ្ងៃនេះហើយ។"}

    now = now_kh()
    doc = {
        "employee_id":  employee["_id"],
        "work_date":    today,
        "check_in":     now,
        "check_out":    None,
        "location_gps": location_gps,
        "status":       "present",
    }
    await attendance_logs().insert_one(doc)
    return {
        "ok":  True,
        "msg": f"✅ ចូលធ្វើការ ម៉ោង *{now.strftime('%H:%M')}* (ម៉ោងកម្ពុជា)\n"
               f"📅 {today}",
    }


async def check_out(chat_id: str) -> dict:
    employee = await get_employee_by_chat(chat_id)
    if not employee:
        return {"ok": False, "msg": "❌ អ្នកមិនទាន់ចុះឈ្មោះ។"}

    today = today_kh()
    log   = await attendance_logs().find_one(
        {"employee_id": employee["_id"], "work_date": today, "check_out": None}
    )
    if not log:
        return {"ok": False, "msg": "⚠️ រកមិនឃើញការចូលធ្វើការថ្ងៃនេះ។"}

    now = now_kh()
    # Calculate hours worked
    cin = log.get("check_in")
    if cin:
        if cin.tzinfo is None:
            cin = cin.replace(tzinfo=timezone.utc).astimezone(KH_TZ)
        worked = now - cin
        total_hours = int(worked.total_seconds() // 3600)
        total_mins  = int((worked.total_seconds() % 3600) // 60)
        worked_str  = f"{total_hours}ម៉ោង {total_mins}នាទី"
    else:
        worked_str = "—"

    await attendance_logs().update_one(
        {"_id": log["_id"]},
        {"$set": {"check_out": now}}
    )
    return {
        "ok":  True,
        "msg": f"🚪 ចេញពីធ្វើការ ម៉ោង *{now.strftime('%H:%M')}* (ម៉ោងកម្ពុជា)\n"
               f"📅 {today}\n"
               f"⏱ សរុបធ្វើការ: *{worked_str}*",
    }


async def my_attendance(chat_id: str) -> str:
    employee = await get_employee_by_chat(chat_id)
    if not employee:
        return "❌ អ្នកមិនទាន់ចុះឈ្មោះ។"

    cursor = attendance_logs().find(
        {"employee_id": employee["_id"]}
    ).sort("work_date", -1).limit(7)

    logs = await cursor.to_list(length=7)
    if not logs:
        return "📋 មិនមានទំនាក់ទំនងវត្តមានទេ។"

    lines = ["📋 *វត្តមាន ៧ ថ្ងៃចុងក្រោយ*\n"]
    for l in logs:
        cin  = fmt_kh(l.get("check_in"))
        cout = fmt_kh(l.get("check_out"))
        status_map = {
            "present":  "✅ វត្តមាន",
            "absent":   "❌ អវត្តមាន",
            "late":     "⏰ យឺត",
            "half_day": "🌗 កន្លះថ្ងៃ",
        }
        status = status_map.get(l.get("status",""), l.get("status","—"))
        lines.append(
            f"📅 *{l['work_date']}*\n"
            f"   ចូល: {cin}  |  ចេញ: {cout}\n"
            f"   {status}"
        )
    return "\n".join(lines)
