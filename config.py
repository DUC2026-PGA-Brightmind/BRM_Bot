import os
from dotenv import load_dotenv

load_dotenv()

# ─── Telegram ────────────────────────────────────────────────────────────────
TELEGRAM_USER_TOKEN  = os.getenv("TELEGRAM_USER_TOKEN",  "")
TELEGRAM_ADMIN_TOKEN = os.getenv("TELEGRAM_ADMIN_TOKEN", "")

# Admin Telegram Chat IDs — only these users can access Admin Bot
ADMIN_CHAT_IDS = [
    1804844339,
    1473704251,
]

# Admin employee MongoDB _id list
ADMIN_EMPLOYEE_IDS = [
    "6a38b6630096740c5b4b5268",   # Vathanak
    "6a38bb68ffd584cd6234fe69",   # Tuy Ty
]

# ─── MongoDB ─────────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB",  "bright_mind")

# ─── Redis ───────────────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# ─── App ─────────────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
