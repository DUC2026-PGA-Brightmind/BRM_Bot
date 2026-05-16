# database.py - Database connection and schema setup

import mysql.connector
from config import DB_CONFIG


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    conn = mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        port=DB_CONFIG["port"]
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    cursor.execute(f"USE {DB_CONFIG['database']}")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            full_name VARCHAR(150) NOT NULL,
            employee_id VARCHAR(50) UNIQUE NOT NULL,
            department VARCHAR(100),
            phone VARCHAR(20),
            position VARCHAR(100) DEFAULT '',
            salary DECIMAL(10,2) DEFAULT 0,
            join_date DATE DEFAULT NULL,
            is_admin TINYINT(1) DEFAULT 0,
            is_active TINYINT(1) DEFAULT 1,
            registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            worker_id INT NOT NULL,
            leave_type ENUM('annual','sick','emergency','unpaid') NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            reason TEXT,
            status ENUM('pending','approved','rejected') DEFAULT 'pending',
            admin_note TEXT,
            reviewed_by BIGINT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (worker_id) REFERENCES workers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sick_notes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            worker_id INT NOT NULL,
            file_id VARCHAR(255) NOT NULL,
            file_name VARCHAR(255),
            file_type VARCHAR(50),
            note_date DATE NOT NULL,
            description TEXT,
            status ENUM('pending','reviewed') DEFAULT 'pending',
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (worker_id) REFERENCES workers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payslips (
            id INT AUTO_INCREMENT PRIMARY KEY,
            worker_id INT NOT NULL,
            month VARCHAR(20) NOT NULL,
            year INT NOT NULL,
            file_id VARCHAR(255) NOT NULL,
            file_name VARCHAR(255),
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (worker_id) REFERENCES workers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            worker_id INT,
            message TEXT NOT NULL,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Attendance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            worker_id INT NOT NULL,
            work_date DATE NOT NULL,
            check_in DATETIME DEFAULT NULL,
            check_out DATETIME DEFAULT NULL,
            status ENUM('present','absent','half_day','late') DEFAULT 'present',
            note TEXT DEFAULT NULL,
            UNIQUE KEY unique_worker_date (worker_id, work_date),
            FOREIGN KEY (worker_id) REFERENCES workers(id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database initialized successfully.")


# ══════════════════════════════════════════════════════════════════
#  WORKER HELPERS
# ══════════════════════════════════════════════════════════════════

def get_worker_by_telegram_id(telegram_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM workers WHERE telegram_id = %s", (telegram_id,))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return row

def get_worker_by_id(worker_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM workers WHERE id = %s", (worker_id,))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return row

def get_worker_by_employee_id(employee_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM workers WHERE employee_id = %s", (employee_id,))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return row

def register_worker(telegram_id, full_name, employee_id, department, phone):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO workers (telegram_id, full_name, employee_id, department, phone) VALUES (%s,%s,%s,%s,%s)",
        (telegram_id, full_name, employee_id, department, phone)
    )
    conn.commit()
    wid = cursor.lastrowid
    cursor.close(); conn.close()
    return wid

def get_all_workers():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM workers WHERE is_admin = 0 ORDER BY full_name")
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def get_all_workers_including_admin():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM workers ORDER BY full_name")
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def update_worker(worker_id, full_name, department, phone, position, salary, join_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE workers SET full_name=%s, department=%s, phone=%s,
           position=%s, salary=%s, join_date=%s WHERE id=%s""",
        (full_name, department, phone, position, salary, join_date, worker_id)
    )
    conn.commit()
    cursor.close(); conn.close()

def deactivate_worker(worker_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE workers SET is_active=0 WHERE id=%s", (worker_id,))
    conn.commit()
    cursor.close(); conn.close()

def search_workers(keyword):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    kw = f"%{keyword}%"
    cursor.execute(
        """SELECT * FROM workers WHERE is_admin=0 AND
           (full_name LIKE %s OR employee_id LIKE %s OR department LIKE %s)""",
        (kw, kw, kw)
    )
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def get_departments():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT department FROM workers WHERE department IS NOT NULL AND department != ''")
    rows = [r[0] for r in cursor.fetchall()]
    cursor.close(); conn.close()
    return rows

def get_workers_by_department(dept):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM workers WHERE department=%s AND is_admin=0", (dept,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows


# ══════════════════════════════════════════════════════════════════
#  LEAVE HELPERS
# ══════════════════════════════════════════════════════════════════

def create_leave_request(worker_id, leave_type, start_date, end_date, reason):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO leave_requests (worker_id,leave_type,start_date,end_date,reason) VALUES (%s,%s,%s,%s,%s)",
        (worker_id, leave_type, start_date, end_date, reason)
    )
    conn.commit()
    rid = cursor.lastrowid
    cursor.close(); conn.close()
    return rid

def get_leave_requests_by_worker(worker_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM leave_requests WHERE worker_id=%s ORDER BY created_at DESC", (worker_id,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def get_pending_leave_requests():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT lr.*, w.full_name, w.employee_id, w.department, w.telegram_id as wtid
        FROM leave_requests lr JOIN workers w ON lr.worker_id=w.id
        WHERE lr.status='pending' ORDER BY lr.created_at ASC
    """)
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def get_all_leave_requests(status=None, dept=None, year=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    q = """SELECT lr.*, w.full_name, w.employee_id, w.department
           FROM leave_requests lr JOIN workers w ON lr.worker_id=w.id WHERE 1=1"""
    params = []
    if status:
        q += " AND lr.status=%s"; params.append(status)
    if dept:
        q += " AND w.department=%s"; params.append(dept)
    if year:
        q += " AND YEAR(lr.start_date)=%s"; params.append(year)
    q += " ORDER BY lr.created_at DESC"
    cursor.execute(q, params)
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def update_leave_status(leave_id, status, admin_note="", reviewed_by=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE leave_requests SET status=%s, admin_note=%s, reviewed_by=%s WHERE id=%s",
        (status, admin_note, reviewed_by, leave_id)
    )
    conn.commit()
    cursor.close(); conn.close()

def get_leave_request_by_id(leave_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT lr.*, w.telegram_id, w.full_name, w.employee_id, w.department
           FROM leave_requests lr JOIN workers w ON lr.worker_id=w.id WHERE lr.id=%s""",
        (leave_id,)
    )
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return row


# ══════════════════════════════════════════════════════════════════
#  SICK NOTE HELPERS
# ══════════════════════════════════════════════════════════════════

def save_sick_note(worker_id, file_id, file_name, file_type, note_date, description):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sick_notes (worker_id,file_id,file_name,file_type,note_date,description) VALUES (%s,%s,%s,%s,%s,%s)",
        (worker_id, file_id, file_name, file_type, note_date, description)
    )
    conn.commit()
    nid = cursor.lastrowid
    cursor.close(); conn.close()
    return nid

def get_sick_notes_by_worker(worker_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM sick_notes WHERE worker_id=%s ORDER BY uploaded_at DESC", (worker_id,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def get_pending_sick_notes():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT sn.*, w.full_name, w.employee_id, w.department
        FROM sick_notes sn JOIN workers w ON sn.worker_id=w.id
        WHERE sn.status='pending' ORDER BY sn.uploaded_at ASC
    """)
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def get_all_sick_notes():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT sn.*, w.full_name, w.employee_id, w.department
        FROM sick_notes sn JOIN workers w ON sn.worker_id=w.id
        ORDER BY sn.uploaded_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows


# ══════════════════════════════════════════════════════════════════
#  PAYSLIP HELPERS
# ══════════════════════════════════════════════════════════════════

def save_payslip(worker_id, month, year, file_id, file_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO payslips (worker_id,month,year,file_id,file_name) VALUES (%s,%s,%s,%s,%s)",
        (worker_id, month, year, file_id, file_name)
    )
    conn.commit()
    sid = cursor.lastrowid
    cursor.close(); conn.close()
    return sid

def get_payslips_by_worker(worker_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM payslips WHERE worker_id=%s ORDER BY year DESC, sent_at DESC", (worker_id,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def get_all_payslips():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, w.full_name, w.employee_id, w.department
        FROM payslips p JOIN workers w ON p.worker_id=w.id
        ORDER BY p.sent_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows


# ══════════════════════════════════════════════════════════════════
#  ANALYTICS / REPORTING
# ══════════════════════════════════════════════════════════════════

def get_dashboard_stats():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    stats = {}

    cursor.execute("SELECT COUNT(*) as c FROM workers WHERE is_admin=0")
    stats["total_workers"] = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM leave_requests WHERE status='pending'")
    stats["pending_leaves"] = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM leave_requests WHERE status='approved' AND MONTH(start_date)=MONTH(CURDATE()) AND YEAR(start_date)=YEAR(CURDATE())")
    stats["approved_this_month"] = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM sick_notes WHERE status='pending'")
    stats["pending_sick_notes"] = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM payslips WHERE MONTH(sent_at)=MONTH(CURDATE()) AND YEAR(sent_at)=YEAR(CURDATE())")
    stats["payslips_this_month"] = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM leave_requests WHERE MONTH(created_at)=MONTH(CURDATE()) AND YEAR(created_at)=YEAR(CURDATE())")
    stats["leaves_this_month"] = cursor.fetchone()["c"]

    cursor.close(); conn.close()
    return stats

def get_leave_analytics(year=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    y = year or __import__('datetime').datetime.now().year

    # By type
    cursor.execute("""
        SELECT leave_type, COUNT(*) as total,
               SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) as approved,
               SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) as rejected,
               SUM(CASE WHEN status='pending'  THEN 1 ELSE 0 END) as pending
        FROM leave_requests WHERE YEAR(start_date)=%s GROUP BY leave_type
    """, (y,))
    by_type = cursor.fetchall()

    # By department
    cursor.execute("""
        SELECT w.department, COUNT(*) as total,
               SUM(CASE WHEN lr.status='approved' THEN 1 ELSE 0 END) as approved
        FROM leave_requests lr JOIN workers w ON lr.worker_id=w.id
        WHERE YEAR(lr.start_date)=%s GROUP BY w.department ORDER BY total DESC
    """, (y,))
    by_dept = cursor.fetchall()

    # By month
    cursor.execute("""
        SELECT MONTH(start_date) as month, COUNT(*) as total
        FROM leave_requests WHERE YEAR(start_date)=%s
        GROUP BY MONTH(start_date) ORDER BY month
    """, (y,))
    by_month = cursor.fetchall()

    # Top leave takers
    cursor.execute("""
        SELECT w.full_name, w.employee_id, w.department, COUNT(*) as total_requests,
               SUM(DATEDIFF(lr.end_date, lr.start_date)+1) as total_days
        FROM leave_requests lr JOIN workers w ON lr.worker_id=w.id
        WHERE lr.status='approved' AND YEAR(lr.start_date)=%s
        GROUP BY w.id ORDER BY total_days DESC LIMIT 10
    """, (y,))
    top_takers = cursor.fetchall()

    cursor.close(); conn.close()
    return {"by_type": by_type, "by_dept": by_dept, "by_month": by_month, "top_takers": top_takers, "year": y}

def get_worker_leave_summary(worker_id, year=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    y = year or __import__('datetime').datetime.now().year
    cursor.execute("""
        SELECT leave_type, status, COUNT(*) as count,
               SUM(DATEDIFF(end_date, start_date)+1) as days
        FROM leave_requests WHERE worker_id=%s AND YEAR(start_date)=%s
        GROUP BY leave_type, status
    """, (worker_id, y))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

# ══════════════════════════════════════════════════════════════════
#  ATTENDANCE HELPERS
# ══════════════════════════════════════════════════════════════════

def get_today_attendance(worker_id):
    """Get today's attendance record for a worker."""
    from datetime import date
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM attendance WHERE worker_id=%s AND work_date=%s",
        (worker_id, date.today())
    )
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return row


def check_in(worker_id):
    """Record check-in. Returns (success, message_kh)."""
    from datetime import date, datetime
    today = date.today()
    now = datetime.now()

    # Check-in allowed: 12 AM (00:00) to 12 PM (12:00)
    if not (0 <= now.hour < 12):
        return False, f"⚠️ ម៉ោងចូលធ្វើការ គឺ ១២ យប់ ដល់ ១២ ថ្ងៃត្រង់ប៉ុណ្ណោះ។\nឥឡូវ: {now.strftime('%H:%M')}"

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if already checked in today
    cursor.execute(
        "SELECT * FROM attendance WHERE worker_id=%s AND work_date=%s",
        (worker_id, today)
    )
    existing = cursor.fetchone()

    if existing and existing["check_in"]:
        cursor.close(); conn.close()
        check_in_time = existing["check_in"].strftime("%H:%M") if hasattr(existing["check_in"], "strftime") else str(existing["check_in"])
        return False, f"⚠️ អ្នកបានចូលធ្វើការហើយ នៅម៉ោង *{check_in_time}* ។"

    # Determine status: late if after 8:00 AM
    status = "late" if now.hour >= 8 else "present"

    try:
        if existing:
            cursor.execute(
                "UPDATE attendance SET check_in=%s, status=%s WHERE worker_id=%s AND work_date=%s",
                (now, status, worker_id, today)
            )
        else:
            cursor.execute(
                "INSERT INTO attendance (worker_id, work_date, check_in, status) VALUES (%s,%s,%s,%s)",
                (worker_id, today, now, status)
            )
        conn.commit()
        cursor.close(); conn.close()
        status_kh = "យឺត" if status == "late" else "ទាន់ម៉ោង"
        return True, f"✅ *បានចូលធ្វើការ!*\n🕐 ម៉ោង: *{now.strftime('%H:%M')}*\n📅 ថ្ងៃ: {today}\n📌 ស្ថានភាព: {status_kh}"
    except Exception as e:
        cursor.close(); conn.close()
        return False, f"❌ កំហុស: {e}"


def check_out(worker_id):
    """Record check-out. Returns (success, message_kh)."""
    from datetime import date, datetime
    today = date.today()
    now = datetime.now()

    # Check-out allowed: 12 PM (12:00) to 12 AM next day (24:00)
    if not (12 <= now.hour <= 23):
        return False, f"⚠️ ម៉ោងចេញធ្វើការ គឺ ១២ ថ្ងៃត្រង់ ដល់ ១២ យប់ប៉ុណ្ណោះ។\nឥឡូវ: {now.strftime('%H:%M')}"

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM attendance WHERE worker_id=%s AND work_date=%s",
        (worker_id, today)
    )
    existing = cursor.fetchone()

    if not existing or not existing["check_in"]:
        cursor.close(); conn.close()
        return False, "⚠️ អ្នកមិនទាន់បានចូលធ្វើការទេ។ សូមចូលធ្វើការជាមុនសិន។"

    if existing["check_out"]:
        check_out_time = existing["check_out"].strftime("%H:%M") if hasattr(existing["check_out"], "strftime") else str(existing["check_out"])
        cursor.close(); conn.close()
        return False, f"⚠️ អ្នកបានចេញធ្វើការហើយ នៅម៉ោង *{check_out_time}* ។"

    try:
        # Calculate hours worked
        check_in_dt = existing["check_in"]
        if hasattr(check_in_dt, "hour"):
            delta = now - check_in_dt
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            duration = f"{hours} ម៉ោង {minutes} នាទី"
        else:
            duration = "—"

        cursor.execute(
            "UPDATE attendance SET check_out=%s WHERE worker_id=%s AND work_date=%s",
            (now, worker_id, today)
        )
        conn.commit()
        cursor.close(); conn.close()
        return True, (
            f"✅ *បានចេញធ្វើការ!*\n"
            f"🕔 ម៉ោង: *{now.strftime('%H:%M')}*\n"
            f"📅 ថ្ងៃ: {today}\n"
            f"⏱ រយៈពេលធ្វើការ: {duration}"
        )
    except Exception as e:
        cursor.close(); conn.close()
        return False, f"❌ កំហុស: {e}"


def get_attendance_by_worker(worker_id, month=None, year=None):
    """Get attendance records for a worker, optionally filtered by month/year."""
    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    now = datetime.now()
    m = month or now.month
    y = year or now.year
    cursor.execute(
        """SELECT * FROM attendance
           WHERE worker_id=%s AND MONTH(work_date)=%s AND YEAR(work_date)=%s
           ORDER BY work_date DESC""",
        (worker_id, m, y)
    )
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows


def get_all_attendance_today():
    """Get all workers' attendance for today (admin view)."""
    from datetime import date
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.*, w.full_name, w.employee_id, w.department
        FROM attendance a JOIN workers w ON a.worker_id=w.id
        WHERE a.work_date=%s ORDER BY a.check_in ASC
    """, (date.today(),))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows


def get_attendance_summary(month=None, year=None):
    """Monthly attendance summary per worker (admin analytics)."""
    from datetime import datetime
    now = datetime.now()
    m = month or now.month
    y = year or now.year
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT w.full_name, w.employee_id, w.department,
               COUNT(*) as total_days,
               SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END) as present,
               SUM(CASE WHEN a.status='late'    THEN 1 ELSE 0 END) as late,
               SUM(CASE WHEN a.status='absent'  THEN 1 ELSE 0 END) as absent,
               SUM(CASE WHEN a.check_out IS NOT NULL THEN
                   TIMESTAMPDIFF(MINUTE, a.check_in, a.check_out) ELSE 0 END) as total_minutes
        FROM attendance a JOIN workers w ON a.worker_id=w.id
        WHERE MONTH(a.work_date)=%s AND YEAR(a.work_date)=%s
        GROUP BY w.id ORDER BY w.full_name
    """, (m, y))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

# ══════════════════════════════════════════════════════════════════
#  SALARY CALCULATION ENGINE
#  Rules:
#   - Base salary: $300/month
#   - Absent without leave: deduct $5/day
#   - Approved leave > 3 days in a month: deduct $5 per extra day
#   - Daily rate = $300 / working_days_in_month
# ══════════════════════════════════════════════════════════════════

BASE_SALARY = 300.0
DEDUCT_PER_DAY = 5.0
FREE_LEAVE_DAYS = 3       # first 3 approved leave days are free
LATE_DEDUCT = 1.0         # optional: $1 deduction per late check-in


def get_working_days_in_month(year, month):
    """Count Mon-Fri working days in a given month."""
    import calendar
    _, days_in_month = calendar.monthrange(year, month)
    count = 0
    for d in range(1, days_in_month + 1):
        import datetime
        if datetime.date(year, month, d).weekday() < 5:  # Mon=0 … Fri=4
            count += 1
    return count


def calculate_salary(worker_id, month, year):
    """
    Calculate net salary for a worker for a given month/year.
    Returns a dict with full breakdown.
    """
    import datetime
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # ── 1. Attendance data ───────────────────────────────────────
    cursor.execute("""
        SELECT work_date, check_in, check_out, status
        FROM attendance
        WHERE worker_id=%s AND MONTH(work_date)=%s AND YEAR(work_date)=%s
        ORDER BY work_date
    """, (worker_id, month, year))
    att_records = cursor.fetchall()

    # ── 2. Approved leave days this month ────────────────────────
    cursor.execute("""
        SELECT start_date, end_date,
               DATEDIFF(end_date, start_date) + 1 AS days
        FROM leave_requests
        WHERE worker_id=%s
          AND status='approved'
          AND (
              (MONTH(start_date)=%s AND YEAR(start_date)=%s)
           OR (MONTH(end_date)=%s   AND YEAR(end_date)=%s)
          )
    """, (worker_id, month, year, month, year))
    leave_records = cursor.fetchall()
    cursor.close(); conn.close()

    working_days = get_working_days_in_month(year, month)
    daily_rate   = BASE_SALARY / working_days if working_days else 0

    # Days actually checked in
    present_days = len([r for r in att_records if r["check_in"]])
    late_days    = len([r for r in att_records if r["status"] == "late"])

    # Total approved leave days (capped to this month's days)
    total_leave_days = 0
    for lr in leave_records:
        # Count only days that fall within this month
        start = lr["start_date"]
        end   = lr["end_date"]
        if hasattr(start, "year"):
            month_start = datetime.date(year, month, 1)
            import calendar
            month_end = datetime.date(year, month, calendar.monthrange(year, month)[1])
            actual_start = max(start, month_start)
            actual_end   = min(end,   month_end)
            if actual_end >= actual_start:
                total_leave_days += (actual_end - actual_start).days + 1
        else:
            total_leave_days += int(lr["days"] or 0)

    # Absent without leave = working days not covered by attendance or leave
    covered_days = present_days + total_leave_days
    absent_no_leave = max(0, working_days - covered_days)

    # Deductions
    # 1) Absent without leave: $5/day
    deduct_absent = absent_no_leave * DEDUCT_PER_DAY

    # 2) Approved leave > 3 days: $5 per extra day
    extra_leave_days = max(0, total_leave_days - FREE_LEAVE_DAYS)
    deduct_leave     = extra_leave_days * DEDUCT_PER_DAY

    # 3) Late deduction (optional, $1/late)
    deduct_late = late_days * LATE_DEDUCT

    total_deductions = deduct_absent + deduct_leave + deduct_late
    net_salary       = max(0.0, BASE_SALARY - total_deductions)

    return {
        "worker_id":        worker_id,
        "month":            month,
        "year":             year,
        "base_salary":      BASE_SALARY,
        "working_days":     working_days,
        "daily_rate":       round(daily_rate, 2),
        "present_days":     present_days,
        "late_days":        late_days,
        "total_leave_days": total_leave_days,
        "extra_leave_days": extra_leave_days,
        "absent_no_leave":  absent_no_leave,
        "deduct_absent":    round(deduct_absent, 2),
        "deduct_leave":     round(deduct_leave, 2),
        "deduct_late":      round(deduct_late, 2),
        "total_deductions": round(total_deductions, 2),
        "net_salary":       round(net_salary, 2),
    }


def calculate_all_salaries(month, year):
    """Calculate salary for every worker for a given month."""
    workers = get_all_workers()
    results = []
    for w in workers:
        calc = calculate_salary(w["id"], month, year)
        calc["full_name"]   = w["full_name"]
        calc["employee_id"] = w["employee_id"]
        calc["department"]  = w["department"]
        results.append(calc)
    return results


def save_salary_record(worker_id, month, year, net_salary, breakdown_json):
    """Save calculated salary to payslips table (as a computed record)."""
    import json
    conn = get_connection()
    cursor = conn.cursor()
    # Use file_id = 'CALCULATED' to mark auto-generated payslips
    cursor.execute("""
        INSERT INTO payslips (worker_id, month, year, file_id, file_name)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE file_id=VALUES(file_id), file_name=VALUES(file_name)
    """, (worker_id, month, year,
          f"CALC:{net_salary}",
          f"salary_{month}_{year}.txt"))
    conn.commit()
    sid = cursor.lastrowid
    cursor.close(); conn.close()
    return sid
