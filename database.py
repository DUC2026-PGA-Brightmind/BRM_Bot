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
