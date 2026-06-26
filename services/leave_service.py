"""
Leave request service.
"""
from datetime import datetime
from database.collections import leave_requests, telegram_sessions, employees


async def get_employee_by_chat(chat_id: str) -> dict | None:
    session = await telegram_sessions().find_one({"telegram_chat_id": str(chat_id)})
    if not session:
        return None
    return await employees().find_one({"_id": session["employee_id"]})


async def submit_leave(chat_id: str, leave_type: str,
                       start_date: str, end_date: str) -> dict:
    employee = await get_employee_by_chat(chat_id)
    if not employee:
        return {"ok": False, "msg": "❌ You are not registered."}

    doc = {
        "employee_id":             employee["_id"],
        "approved_by_manager_id":  None,
        "start_date":              start_date,
        "end_date":                end_date,
        "leave_type":              leave_type,
        "status":                  "pending",
        "requested_at":            datetime.utcnow(),
    }
    result = await leave_requests().insert_one(doc)
    leave_id = str(result.inserted_id)

    # Notify admins via Admin Bot
    try:
        from services.notify_service import notify_leave_request
        await notify_leave_request(
            leave_id    = leave_id,
            employee_id = employee["_id"],
            leave_type  = leave_type,
            start_date  = start_date,
            end_date    = end_date,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Notify failed: {e}")

    return {"ok": True, "msg": f"✅ Leave request submitted!\n\nAdmins have been notified."}


async def my_leaves(chat_id: str) -> str:
    employee = await get_employee_by_chat(chat_id)
    if not employee:
        return "❌ You are not registered."

    cursor = leave_requests().find(
        {"employee_id": employee["_id"]}
    ).sort("requested_at", -1).limit(5)

    logs = await cursor.to_list(length=5)
    if not logs:
        return "📋 No leave requests found."

    lines = ["📋 *Your recent leave requests:*"]
    for l in logs:
        lines.append(
            f"• {l['leave_type'].upper()}  {l['start_date']} → {l['end_date']}  [{l['status']}]"
        )
    return "\n".join(lines)


async def pending_leaves_for_manager() -> list:
    cursor = leave_requests().find({"status": "pending"})
    return await cursor.to_list(length=50)


async def approve_leave(leave_id: str, manager_emp_id) -> dict:
    from bson import ObjectId
    result = await leave_requests().update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {"status": "approved", "approved_by_manager_id": manager_emp_id}}
    )
    if result.modified_count:
        return {"ok": True, "msg": "✅ Leave approved."}
    return {"ok": False, "msg": "❌ Leave request not found."}


async def reject_leave(leave_id: str, manager_emp_id) -> dict:
    from bson import ObjectId
    result = await leave_requests().update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {"status": "rejected", "approved_by_manager_id": manager_emp_id}}
    )
    if result.modified_count:
        return {"ok": True, "msg": "✅ Leave rejected."}
    return {"ok": False, "msg": "❌ Leave request not found."}
