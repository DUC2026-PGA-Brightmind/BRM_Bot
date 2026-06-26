"""
MongoDB collection references.
All documents use the schemas described below.

Collections  ──────────────────────────────────────────────
  departments         → DEPARTMENTS
  roles               → ROLES
  employees           → EMPLOYEES
  telegram_sessions   → TELEGRAM_SESSIONS
  attendance_logs     → ATTENDANCE_LOGS
  leave_requests      → LEAVE_REQUESTS
  payroll_records     → PAYROLL_RECORDS
  payroll_deductions  → PAYROLL_DEDUCTIONS
  material_logs       → MATERIAL_LOGS

Schemas (field reference)
─────────────────────────

departments:
  { _id, name, description, created_at }

roles:
  { _id, title, permissions, created_at }
  permissions: ["worker" | "manager" | "hr_admin" | "super_admin"]

employees:
  { _id, department_id, role_id, first_name, last_name,
    phone_number, email, base_salary, status, hired_at }
  status: ["active" | "inactive" | "terminated"]

telegram_sessions:
  { telegram_chat_id (PK str), employee_id, current_state,
    registration_token, updated_at }

attendance_logs:
  { _id, employee_id, work_date, check_in, check_out,
    location_gps, status }
  status: ["present" | "absent" | "late" | "half_day"]

leave_requests:
  { _id, employee_id, approved_by_manager_id, start_date,
    end_date, leave_type, status, requested_at }
  leave_type: ["annual" | "sick" | "unpaid" | "emergency"]
  status:     ["pending" | "approved" | "rejected"]

payroll_records:
  { _id, employee_id, processed_by_hr_id, pay_period_month,
    total_days_worked, gross_pay, total_deductions, net_pay, status }
  status: ["draft" | "approved" | "paid"]

payroll_deductions:
  { _id, payroll_record_id, type, amount, description }
  type: ["tax" | "advance" | "penalty" | "other"]

material_logs:
  { _id, employee_id, material_name, quantity_adjusted,
    unit, transaction_type, logged_at }
  unit:             ["pcs" | "kg" | "liter" | "box"]
  transaction_type: ["in" | "out" | "adjustment"]
"""

from database.mongo import get_db


def departments():       return get_db()["departments"]
def roles():             return get_db()["roles"]
def employees():         return get_db()["employees"]
def telegram_sessions(): return get_db()["telegram_sessions"]
def attendance_logs():   return get_db()["attendance_logs"]
def leave_requests():    return get_db()["leave_requests"]
def payroll_records():   return get_db()["payroll_records"]
def payroll_deductions():return get_db()["payroll_deductions"]
def material_logs():     return get_db()["material_logs"]
