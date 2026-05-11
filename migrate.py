# migrate.py - Add missing columns to existing database tables

import mysql.connector
from config import DB_CONFIG

conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor()

migrations = [
    # leave_requests: add reviewed_by
    ("leave_requests", "reviewed_by",
     "ALTER TABLE leave_requests ADD COLUMN reviewed_by BIGINT DEFAULT NULL"),

    # workers: add position
    ("workers", "position",
     "ALTER TABLE workers ADD COLUMN position VARCHAR(100) DEFAULT NULL"),

    # workers: add salary
    ("workers", "salary",
     "ALTER TABLE workers ADD COLUMN salary DECIMAL(10,2) DEFAULT 0"),

    # workers: add join_date
    ("workers", "join_date",
     "ALTER TABLE workers ADD COLUMN join_date DATE DEFAULT NULL"),

    # workers: add is_active
    ("workers", "is_active",
     "ALTER TABLE workers ADD COLUMN is_active TINYINT(1) DEFAULT 1"),
]

for table, col, sql in migrations:
    try:
        cursor.execute(sql)
        conn.commit()
        print(f"[OK] Added column '{col}' to '{table}'")
    except mysql.connector.errors.DatabaseError as e:
        if "1060" in str(e):
            print(f"[--] Column '{col}' in '{table}' already exists")
        else:
            print(f"[ERR] {table}.{col}: {e}")

cursor.close()
conn.close()
print("\nMigration complete.")
