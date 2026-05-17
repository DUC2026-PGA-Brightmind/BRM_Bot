# config.py - Reads from environment variables (Railway/VPS)
# or falls back to hardcoded values (local XAMPP)

import os

# ── Bot Tokens ───────────────────────────────────────────────────
BOT_TOKEN       = os.getenv("BOT_TOKEN",       "8628273038:AAHNtr9XZM4zlMQwfWqhSdtfrbJFt9FsQIc")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "8720658078:AAFRPP5TjYK-78vUqVKdfSXtKS6GVazibxI")

# ── Database ─────────────────────────────────────────────────────
# Railway provides MYSQL_URL or individual vars
DB_CONFIG = {
    "host":     os.getenv("MYSQLHOST",     os.getenv("DB_HOST",     "localhost")),
    "user":     os.getenv("MYSQLUSER",     os.getenv("DB_USER",     "root")),
    "password": os.getenv("MYSQLPASSWORD", os.getenv("DB_PASSWORD", "")),
    "database": os.getenv("MYSQLDATABASE", os.getenv("DB_NAME",     "hr_bot_db")),
    "port":     int(os.getenv("MYSQLPORT", os.getenv("DB_PORT",     "3306"))),
}

# ── Admin IDs ────────────────────────────────────────────────────
# Set as comma-separated string in Railway env: "123456789,987654321"
_admin_ids_str = os.getenv("ADMIN_IDS", "1800044339,1473704251")
ADMIN_IDS = [int(x.strip()) for x in _admin_ids_str.split(",") if x.strip()]

# ── Folders ──────────────────────────────────────────────────────
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
EXPORT_FOLDER = os.getenv("EXPORT_FOLDER", "exports")
