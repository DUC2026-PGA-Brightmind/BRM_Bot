"""
Payroll — ប្រាក់ខែគោល $300/ខែ
  - ថ្ងៃធ្វើការ 26 ថ្ងៃ/ខែ → rate = 300/26 ≈ $11.54/ថ្ងៃ
  - ឈប់ (late/absent) >= 3 ដង → កាត់ 1 ថ្ងៃ ($5) ក្នុង 3 ដង
"""
from datetime import datetime
from bson import ObjectId
from database.collections import attendance_logs, employees, telegram_sessions

BASE_SALARY  = 300.0   # $ per month
WORK_DAYS    = 26      # working days per month
PENALTY_RATE = 5.0     # $ deducted per every 3 late/absent occurrences


async def calc_payroll(employee_id, pay_period_month: str) -> dict:
    emp = await employees().find_one({"_id": employee_id})
    if not emp:
        return {}

    cursor = attendance_logs().find({
        "employee_id": employee_id,
        "work_date":   {"$regex": f"^{pay_period_month}"},
    })
    logs = await cursor.to_list(length=31)

    present   = sum(1 for l in logs if l.get("status") == "present")
    late      = sum(1 for l in logs if l.get("status") == "late")
    half_day  = sum(1 for l in logs if l.get("status") == "half_day")
    absent    = sum(1 for l in logs if l.get("status") == "absent")

    daily_rate   = BASE_SALARY / WORK_DAYS
    # effective days worked
    eff_days     = present + (half_day * 0.5) + late
    gross        = round(daily_rate * eff_days, 2)

    # penalty: every 3 late+absent occurrences → deduct $5
    penalty_count = (late + absent) // 3
    deduction     = round(penalty_count * PENALTY_RATE, 2)
    net_pay       = round(gross - deduction, 2)

    return {
        "emp":           emp,
        "period":        pay_period_month,
        "present":       present,
        "late":          late,
        "half_day":      half_day,
        "absent":        absent,
        "gross":         gross,
        "deduction":     deduction,
        "penalty_count": penalty_count,
        "net_pay":       net_pay,
        "daily_rate":    round(daily_rate, 2),
    }


async def get_all_payroll(pay_period_month: str) -> list:
    sessions = await telegram_sessions().find({}).to_list(length=200)
    results  = []
    for sess in sessions:
        data = await calc_payroll(sess["employee_id"], pay_period_month)
        if data:
            data["telegram_chat_id"] = sess["telegram_chat_id"]
            results.append(data)
    return results
