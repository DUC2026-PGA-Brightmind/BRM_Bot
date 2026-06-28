"""
Attendance service — ម៉ោងកម្ពុជា (UTC+7)

Rules:
  Check-in:
    ≤ 08:00  → present  ✅
    > 08:00  → late     ⏰
  Check-out:
    Standard finish: 18:00 (6 PM)
    Worker can check-out any time after check-in.
"""
from datetime import datetime, date, timezone, timedelta
from database.collections import attendance_logs, employees, telegram_sessions

# ── Cambodia timezone UTC+7 ───────────────────────────────────────────────────
KH_TZ = timezone(timedelta(hours=7))

CHECK_IN_CUTOFF  = 8   # 08:00 — on time threshold
CHECK_OUT_STD    = 18  # 18:00 — standard end of work


def now_kh() -> datetime:
    return datetime.now(KH_TZ)

def today_kh() -> str:
    return now_kh().date().isoformat()

def fmt_kh(dt: datetime) -> str:
    if dt is None:
        return "--:--"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KH_TZ).strftime("%H:%M")

def to_kh(dt: datetime) -> datetime:
    if dt is None:
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KH_TZ)


# ── Helpers ───────────────────────────────────────────────────────────────────
async def get_employee_by_chat(chat_id: str) -> dict | None:
    session = await telegram_sessions().find_one({"telegram_chat_id": str(chat_id)})
    if not session:
        return None
    return await employees().find_one({"_id": session["employee_id"]})


# ═════════════════════════════════════════════════════════════════════════════
#  CHECK-IN
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
        cin_time = fmt_kh(existing["check_in"])
        return {"ok": False, "msg": f"⚠️ អ្នកបានចូលធ្វើការថ្ងៃនេះហើយ ម៉ោង {cin_time}។"}

    now  = now_kh()
    hour = now.hour
    mins = now.minute

    # Determine status
    if hour < CHECK_IN_CUTOFF or (hour == CHECK_IN_CUTOFF and mins == 0):
        status   = "present"
        status_msg = "✅ ចូលធ្វើការទាន់ម៉ោង"
    else:
        status   = "late"
        late_mins = (hour - CHECK_IN_CUTOFF) * 60 + mins
        status_msg = f"⏰ ចូលធ្វើការយឺត {late_mins} នាទី"

    doc = {
        "employee_id":  employee["_id"],
        "work_date":    today,
        "check_in":     now,
        "check_out":    None,
        "location_gps": location_gps,
        "status":       status,
    }
    await attendance_logs().insert_one(doc)
    return {
        "ok":  True,
        "msg": (
            f"{status_msg}\n\n"
            f"🕐 ម៉ោងចូល  : *{now.strftime('%H:%M')}*\n"
            f"📅 កាលបរិច្ឆេទ : {today}\n"
            f"🏢 ម៉ោងការ   : 08:00 — 18:00"
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
#  CHECK-OUT
# ═════════════════════════════════════════════════════════════════════════════
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
    cin = to_kh(log.get("check_in"))
    if cin:
        worked       = now - cin
        total_secs   = int(worked.total_seconds())
        total_hours  = total_secs // 3600
        total_mins   = (total_secs % 3600) // 60
        worked_str   = f"{total_hours}ម៉ោង {total_mins}នាទី"
    else:
        worked_str = "—"

    # Early / on time checkout note
    if now.hour < CHECK_OUT_STD:
        early_mins  = (CHECK_OUT_STD - now.hour) * 60 - now.minute
        checkout_note = f"⚠️ ចេញមុនម៉ោង {early_mins} នាទី"
    else:
        checkout_note = "✅ ចេញត្រឹមម៉ោង / ក្រោយម៉ោង"

    await attendance_logs().update_one(
        {"_id": log["_id"]},
        {"$set": {"check_out": now}}
    )
    return {
        "ok":  True,
        "msg": (
            f"🚪 *ចេញពីធ្វើការ*\n\n"
            f"🕕 ម៉ោងចេញ    : *{now.strftime('%H:%M')}*\n"
            f"📅 កាលបរិច្ឆេទ  : {today}\n"
            f"⏱ សរុបធ្វើការ : *{worked_str}*\n"
            f"{checkout_note}"
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
#  MY ATTENDANCE
# ═════════════════════════════════════════════════════════════════════════════
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

    status_map = {
        "present":  "✅ វត្តមាន",
        "absent":   "❌ អវត្តមាន",
        "late":     "⏰ យឺត",
        "half_day": "🌗 កន្លះថ្ងៃ",
    }

    lines = ["📋 *វត្តមាន ៧ ថ្ងៃចុងក្រោយ*\n"]
    for l in logs:
        cin    = fmt_kh(l.get("check_in"))
        cout   = fmt_kh(l.get("check_out"))
        status = status_map.get(l.get("status",""), l.get("status","—"))

        # Calculate worked hours if both in/out exist
        if l.get("check_in") and l.get("check_out"):
            ci = to_kh(l["check_in"])
            co = to_kh(l["check_out"])
            secs  = int((co - ci).total_seconds())
            h, m  = secs // 3600, (secs % 3600) // 60
            dur   = f"⏱ {h}ម៉ោង{m}នាទី"
        else:
            dur = "⏱ —"

        lines.append(
            f"📅 *{l['work_date']}*  {status}\n"
            f"   ចូល {cin}  →  ចេញ {cout}  {dur}"
        )
    return "\n".join(lines)
