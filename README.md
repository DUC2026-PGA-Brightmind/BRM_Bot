# BrightMind HR Management Bot

A Telegram HR bot system for construction/cleaning firms with 50+ mobile workers.
Two bots: **Worker Bot** (employees) + **Admin Bot** (HR managers).

---

## Features

| Feature | Worker Bot | Admin Bot |
|---|---|---|
| Self-registration | ✅ | — |
| Request leave | ✅ | — |
| Submit sick notes | ✅ | — |
| Check-in / Check-out | ✅ | — |
| View payslips | ✅ | — |
| Approve/Reject leave | — | ✅ |
| Salary auto-calculation | — | ✅ |
| Attendance reports | — | ✅ |
| Export CSV/PDF | — | ✅ |
| Broadcast messages | — | ✅ |
| Employee management | — | ✅ |

---

## Salary Rules
- Base salary: **$300/month**
- Absent without leave: **-$5/day**
- Approved leave > 3 days: **-$5/day** (extra days only)
- Late check-in: **-$1/day**

---

## Tech Stack
- **Language:** Python 3.11
- **Bot Library:** pyTelegramBotAPI
- **Database:** MySQL (Railway)
- **Hosting:** Railway.app
- **Language:** Khmer (ភាសាខ្មែរ)

---

## Project Structure

```
BRM_Bot/
├── bot.py              # Worker Bot entry point
├── admin_bot.py        # Admin Bot entry point
├── run_both.py         # Runs both bots (Railway)
├── config.py           # Config (reads from env vars)
├── database.py         # All MySQL queries + salary calc
├── keyboards.py        # Telegram keyboards
├── states.py           # Conversation states
├── export_utils.py     # CSV + PDF export
├── migrate.py          # DB migrations
├── nixpacks.toml       # Railway build config
├── Procfile            # Railway start command
├── requirements.txt    # Python dependencies
└── handlers/
    ├── registration.py # Worker sign-up
    ├── leave.py        # Leave requests
    ├── sick_note.py    # Sick note upload
    ├── payslip.py      # Payslip view
    ├── attendance.py   # Check-in/out
    └── admin.py        # Worker profile
```

---

## Deploy to Railway

1. Fork/clone this repo
2. Create new Railway project → Deploy from GitHub
3. Add MySQL database service
4. Set environment variables:
   ```
   BOT_TOKEN=your_worker_bot_token
   ADMIN_BOT_TOKEN=your_admin_bot_token
   ADMIN_IDS=your_telegram_id
   ```
5. Link MySQL variables (MYSQLHOST, MYSQLUSER, MYSQLPASSWORD, MYSQLDATABASE, MYSQLPORT)
6. Run migration: `python migrate.py`
7. Start command: `python run_both.py`

---

## Environment Variables

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Worker Bot token from @BotFather |
| `ADMIN_BOT_TOKEN` | Admin Bot token from @BotFather |
| `ADMIN_IDS` | Comma-separated admin Telegram IDs |
| `MYSQLHOST` | MySQL host (auto from Railway) |
| `MYSQLUSER` | MySQL user (auto from Railway) |
| `MYSQLPASSWORD` | MySQL password (auto from Railway) |
| `MYSQLDATABASE` | MySQL database (auto from Railway) |
| `MYSQLPORT` | MySQL port (auto from Railway) |
