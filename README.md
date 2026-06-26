# Bright Mind Technology - Telegram Bot Project

### 🔗 Project Navigation
* **Live Bot:**[hr_life_duc_bot](https://t.me/hr_life_duc_bot)
* **Project Management:** [Kanban board](https://github.com/orgs/DUC2026-PGA-Brightmind/projects/4)
* **Full Documentation:** [Wiki Document](https://github.com/DUC2026-PGA-Brightmind/BRM_Bot/wiki)

### 🛠 Technical Summary
* **Language:** Python
* **Database:** MangoAtlas
* **Mockup Scenario:** HR-Life

# 🌟 Bright Mind — HR Workforce Bot

A Telegram-based HR management system built with Python.

## Features

### 👷 Worker Bot
- Registration (Name, ID, Phone, Role)
- Daily Check-in / Check-out
- Leave requests with admin approval flow
- Export approved leaves as PDF
- View & edit profile

### 🛠️ Admin Bot
- Secured access (whitelist by Telegram Chat ID)
- Unauthorized access alerts
- View & manage all registered workers
- Approve / Reject leave requests with worker notification
- Payroll calculation based on attendance ($300 base, $5 penalty per 3 absences)
- Send payslips to individual or all workers
- Broadcast messages to all workers
- Export PDF reports: Workers, Payroll, Attendance, Leave

## Tech Stack
- **Python 3.11**
- **python-telegram-bot 21**
- **MongoDB Atlas** (Motor async driver)
- **ReportLab** (PDF generation)

## Setup

1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/BRM.git
cd BRM
```

2. Install dependencies
```bash
py -3.11 -m pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your values
```bash
copy .env.example .env
```

4. Run
```bash
py -3.11 main.py
```

## Environment Variables
See `.env.example` for required variables.

## Project Structure
```
BRM/
├── main.py                  # Entry point — runs both bots
├── config.py                # Config loaded from .env
├── requirements.txt
├── bots/
│   ├── user_bot.py          # Worker Bot
│   └── admin_bot.py         # Admin Bot
├── services/
│   ├── attendance_service.py
│   ├── leave_service.py
│   ├── payroll_service.py
│   ├── material_service.py
│   ├── employee_service.py
│   ├── notify_service.py
│   └── pdf_service.py
└── database/
    ├── mongo.py             # Motor async client
    └── collections.py      # Collection references
```
