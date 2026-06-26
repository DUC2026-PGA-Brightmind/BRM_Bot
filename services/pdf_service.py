"""
PDF Export Service — generates reports using ReportLab
Supports Khmer text via a Unicode font fallback.
"""
import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Font setup (tries to use a system Unicode font for Khmer) ─────────────────
_FONT_NAME = "Helvetica"   # fallback

def _register_unicode_font():
    global _FONT_NAME
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                fname = os.path.splitext(os.path.basename(path))[0].capitalize()
                pdfmetrics.registerFont(TTFont(fname, path))
                _FONT_NAME = fname
                return
            except Exception:
                continue

_register_unicode_font()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _styles():
    s = getSampleStyleSheet()
    title = ParagraphStyle("KhTitle", parent=s["Title"],
                           fontName=_FONT_NAME, fontSize=16, spaceAfter=6)
    sub   = ParagraphStyle("KhSub",   parent=s["Normal"],
                           fontName=_FONT_NAME, fontSize=10, spaceAfter=4)
    cell  = ParagraphStyle("KhCell",  parent=s["Normal"],
                           fontName=_FONT_NAME, fontSize=8)
    return title, sub, cell

def _table_style(header_color=colors.HexColor("#1a73e8")):
    return TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  header_color),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",     (0, 0), (-1, 0),  _FONT_NAME),
        ("FONTSIZE",     (0, 0), (-1, 0),  9),
        ("FONTNAME",     (0, 1), (-1, -1), _FONT_NAME),
        ("FONTSIZE",     (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
        ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ])


# ═════════════════════════════════════════════════════════════════════════════
#  1. Workers Report
# ═════════════════════════════════════════════════════════════════════════════
async def generate_workers_pdf() -> io.BytesIO:
    from database.collections import telegram_sessions, employees, attendance_logs
    from datetime import date

    sessions = await telegram_sessions().find({}).to_list(length=500)
    title_s, sub_s, _ = _styles()
    buf      = io.BytesIO()
    doc      = SimpleDocTemplate(buf, pagesize=A4,
                                  leftMargin=1.5*cm, rightMargin=1.5*cm,
                                  topMargin=2*cm,    bottomMargin=2*cm)
    story    = []
    now_str  = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    story.append(Paragraph("Bright Mind — Workers Report", title_s))
    story.append(Paragraph(f"Generated: {now_str}  |  Total: {len(sessions)}", sub_s))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a73e8")))
    story.append(Spacer(1, 0.3*cm))

    headers = ["#", "Name", "Code", "Phone", "Role", "Status", "Hired"]
    rows    = [headers]
    for i, sess in enumerate(sessions, 1):
        try:
            emp = await employees().find_one({"_id": sess["employee_id"]})
            if not emp:
                continue
            name   = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
            hired  = emp.get("hired_at","")
            if hasattr(hired, "strftime"):
                hired = hired.strftime("%Y-%m-%d")
            rows.append([
                str(i),
                name,
                emp.get("employee_code","—"),
                emp.get("phone_number","—"),
                emp.get("role_title","—"),
                emp.get("status","—"),
                str(hired)[:10],
            ])
        except Exception:
            continue

    col_w = [0.8*cm, 4*cm, 2*cm, 2.8*cm, 2.5*cm, 1.8*cm, 2.5*cm]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(_table_style())
    story.append(t)
    doc.build(story)
    buf.seek(0)
    return buf


# ═════════════════════════════════════════════════════════════════════════════
#  2. Payroll Report
# ═════════════════════════════════════════════════════════════════════════════
async def generate_payroll_pdf(pay_period_month: str) -> io.BytesIO:
    from services.payroll_service import get_all_payroll

    workers  = await get_all_payroll(pay_period_month)
    title_s, sub_s, _ = _styles()
    buf      = io.BytesIO()
    doc      = SimpleDocTemplate(buf, pagesize=A4,
                                  leftMargin=1.5*cm, rightMargin=1.5*cm,
                                  topMargin=2*cm,    bottomMargin=2*cm)
    story    = []
    now_str  = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    story.append(Paragraph(f"Bright Mind — Payroll {pay_period_month}", title_s))
    story.append(Paragraph(f"Generated: {now_str}  |  Base: $300/month  |  Penalty: $5 per 3 late/absent", sub_s))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a73e8")))
    story.append(Spacer(1, 0.3*cm))

    headers = ["#", "Name", "Code", "Present", "Late", "Half", "Absent",
               "Gross ($)", "Deduct ($)", "Net ($)"]
    rows    = [headers]
    total_net = 0.0

    for i, w in enumerate(workers, 1):
        emp  = w["emp"]
        name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
        total_net += w["net_pay"]
        rows.append([
            str(i), name,
            emp.get("employee_code","—"),
            str(w["present"]),
            str(w["late"]),
            str(w["half_day"]),
            str(w["absent"]),
            f"{w['gross']:.2f}",
            f"{w['deduction']:.2f}",
            f"{w['net_pay']:.2f}",
        ])

    # Total row
    rows.append(["", "TOTAL", "", "", "", "", "", "", "",
                 f"{total_net:.2f}"])

    col_w = [0.6*cm, 3.5*cm, 1.8*cm, 1.5*cm, 1.2*cm,
             1.2*cm, 1.5*cm, 2*cm, 2*cm, 2*cm]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    ts = _table_style()
    # Highlight total row
    ts.add("BACKGROUND", (0, len(rows)-1), (-1, len(rows)-1),
           colors.HexColor("#fce8b2"))
    ts.add("FONTNAME",   (0, len(rows)-1), (-1, len(rows)-1), _FONT_NAME)
    t.setStyle(ts)
    story.append(t)
    doc.build(story)
    buf.seek(0)
    return buf


# ═════════════════════════════════════════════════════════════════════════════
#  3. Attendance Report
# ═════════════════════════════════════════════════════════════════════════════
async def generate_attendance_pdf(pay_period_month: str) -> io.BytesIO:
    from database.collections import telegram_sessions, employees, attendance_logs

    sessions = await telegram_sessions().find({}).to_list(length=200)
    title_s, sub_s, _ = _styles()
    buf   = io.BytesIO()
    doc   = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=1.5*cm, rightMargin=1.5*cm,
                               topMargin=2*cm,    bottomMargin=2*cm)
    story = []
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    story.append(Paragraph(f"Bright Mind — Attendance {pay_period_month}", title_s))
    story.append(Paragraph(f"Generated: {now_str}", sub_s))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a73e8")))
    story.append(Spacer(1, 0.3*cm))

    headers = ["#", "Name", "Code", "Date", "Check-in", "Check-out", "Status"]
    rows    = [headers]
    idx     = 1

    for sess in sessions:
        try:
            emp = await employees().find_one({"_id": sess["employee_id"]})
            if not emp:
                continue
            name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
            code = emp.get("employee_code","—")
            logs = await attendance_logs().find({
                "employee_id": sess["employee_id"],
                "work_date":   {"$regex": f"^{pay_period_month}"},
            }).sort("work_date", 1).to_list(length=31)

            for l in logs:
                cin  = l.get("check_in")
                cout = l.get("check_out")
                rows.append([
                    str(idx), name, code,
                    l.get("work_date","—"),
                    cin.strftime("%H:%M")  if cin  else "—",
                    cout.strftime("%H:%M") if cout else "—",
                    l.get("status","—"),
                ])
                idx += 1
        except Exception:
            continue

    col_w = [0.6*cm, 3.5*cm, 1.8*cm, 2.5*cm, 2*cm, 2*cm, 2*cm]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(_table_style(colors.HexColor("#2e7d32")))
    story.append(t)
    doc.build(story)
    buf.seek(0)
    return buf


# ═════════════════════════════════════════════════════════════════════════════
#  4. Approved Leave Report for a single worker
# ═════════════════════════════════════════════════════════════════════════════
async def generate_leave_pdf(employee_id) -> io.BytesIO:
    from database.collections import leave_requests, employees

    emp = await employees().find_one({"_id": employee_id})
    if not emp:
        raise ValueError("Employee not found")

    name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
    code = emp.get("employee_code", "—")

    leaves = await leave_requests().find({
        "employee_id": employee_id,
        "status":      "approved",
    }).sort("start_date", 1).to_list(length=100)

    title_s, sub_s, _ = _styles()
    buf   = io.BytesIO()
    doc   = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=1.5*cm, rightMargin=1.5*cm,
                               topMargin=2*cm,    bottomMargin=2*cm)
    story = []
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    story.append(Paragraph(f"Bright Mind — Leave Report", title_s))
    story.append(Paragraph(
        f"Worker: {name}  ({code})  |  Generated: {now_str}  |  Total approved: {len(leaves)}",
        sub_s))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e67e22")))
    story.append(Spacer(1, 0.3*cm))

    if not leaves:
        story.append(Paragraph("No approved leave records found.", sub_s))
    else:
        headers = ["#", "Type", "Start Date", "End Date", "Days", "Status"]
        rows    = [headers]
        total_days = 0
        for i, l in enumerate(leaves, 1):
            try:
                from datetime import date
                s = date.fromisoformat(l.get("start_date",""))
                e = date.fromisoformat(l.get("end_date",""))
                days = (e - s).days + 1
            except Exception:
                days = "—"
            if isinstance(days, int):
                total_days += days
            rows.append([
                str(i),
                l.get("leave_type","—"),
                l.get("start_date","—"),
                l.get("end_date","—"),
                str(days),
                "✓ Approved",
            ])
        rows.append(["", "TOTAL", "", "", str(total_days) + " days", ""])

        col_w = [0.8*cm, 3.5*cm, 3*cm, 3*cm, 2*cm, 3*cm]
        t = Table(rows, colWidths=col_w, repeatRows=1)
        ts = _table_style(colors.HexColor("#e67e22"))
        ts.add("BACKGROUND", (0, len(rows)-1), (-1, len(rows)-1),
               colors.HexColor("#fdebd0"))
        t.setStyle(ts)
        story.append(t)

    doc.build(story)
    buf.seek(0)
    return buf
