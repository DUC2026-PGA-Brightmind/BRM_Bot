# config.example.py
# Copy this file to config.py and fill in your actual values
# NEVER commit config.py to GitHub

# Worker Bot Token — get from @BotFather on Telegram
BOT_TOKEN = "YOUR_WORKER_BOT_TOKEN"

# Admin Bot Token — get from @BotFather on Telegram
ADMIN_BOT_TOKEN = "YOUR_ADMIN_BOT_TOKEN"

# MySQL / XAMPP Database config
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",        # Default XAMPP password is empty
    "database": "hr_bot_db",
    "port": 3306
}

# Admin Telegram user IDs
# Get your ID from @userinfobot on Telegram
ADMIN_IDS = [123456789]  # Replace with actual admin Telegram user ID(s)

# File storage folders
UPLOAD_FOLDER = "uploads"
EXPORT_FOLDER = "exports"
