# HR Management Telegram Bot

A Telegram bot for construction/cleaning firms with 50+ mobile workers.  
Handles leave requests, sick note uploads, and payslip distribution — all via Telegram.

---

## Features

| Feature | Workers | Admins |
|---|---|---|
| Self-registration | ✅ | ✅ |
| Request leave (annual/sick/emergency/unpaid) | ✅ | — |
| View leave status | ✅ | — |
| Upload sick notes (photo or PDF) | ✅ | — |
| View payslips | ✅ | — |
| Approve / reject leave requests | — | ✅ |
| View pending sick notes | — | ✅ |
| Send payslips to workers | — | ✅ |
| Broadcast announcements | — | ✅ |
| View all registered workers | — | ✅ |

---

## Requirements

- Python 3.9+
- XAMPP (MySQL running on port 3306)
- Telegram Bot Token

---

## Setup

### 1. Install XAMPP and start MySQL
Open XAMPP Control Panel → Start **Apache** and **MySQL**.

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure the bot
Edit `config.py`:
```python
BOT_TOKEN = "your_bot_token_here"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",        # Default XAMPP password is empty
    "database": "hr_bot_db",
    "port": 3306
}

ADMIN_IDS = [YOUR_TELEGRAM_USER_ID]  # Get your ID from @userinfobot on Telegram
```

### 4. Run the bot
```bash
python bot.py
```

The bot will automatically create the `hr_bot_db` database and all tables on first run.

---

## How to find your Telegram User ID
1. Open Telegram and search for `@userinfobot`
2. Send `/start` — it will reply with your numeric user ID
3. Add that number to `ADMIN_IDS` in `config.py`

---

## Project Structure

```
├── bot.py                  # Main entry point
├── config.py               # Bot token, DB config, admin IDs
├── database.py             # MySQL helpers and schema
├── keyboards.py            # Telegram keyboards
├── states.py               # Conversation state constants
├── requirements.txt
├── uploads/                # Local file cache (auto-created)
└── handlers/
    ├── registration.py     # Worker self-registration
    ├── leave.py            # Leave request flow + admin approval
    ├── sick_note.py        # Sick note upload + admin view
    ├── payslip.py          # Payslip send (admin) + view (worker)
    └── admin.py            # Broadcast, worker list, profile
```

---

## Worker Flow
1. Worker opens bot → `/start`
2. Registers with name, employee ID, department, phone
3. Uses menu to request leave, upload sick notes, view payslips

## Admin Flow
1. Admin opens bot → `/start` (must be registered as worker first)
2. Use `/admin` command to access admin panel
3. Approve/reject leaves, view sick notes, send payslips, broadcast messages

---

## Database Tables

- `workers` — registered employees
- `leave_requests` — all leave requests with status
- `sick_notes` — uploaded sick note file references
- `payslips` — payslip file references per worker per month
- `notifications` — notification log
