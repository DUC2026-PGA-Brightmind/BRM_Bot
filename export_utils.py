# export_utils.py - CSV and PDF export helpers

import csv
import os
from datetime import datetime
from config import EXPORT_FOLDER

os.makedirs(EXPORT_FOLDER, exist_ok=True)

LEAVE_TYPE_KH = {
    "annual": "ច្បាប់ប្រចាំឆ្នាំ",
    "sick": "ច្បាប់ឈឺ",
    "emergency": "ច្បាប់បន្ទាន់",
    "unpaid": "ច្បាប់គ្មានប្រាក់ខែ"
}
STATUS_KH = {"pending": "រង់ចាំ", "approved": "អនុម័ត", "rejected": "បដិសេធ"}
MONTHS_KH = {
    1:"មករា",2:"កុម្ភៈ",3:"មីនា",4:"មេសា",5:"ឧសភា",6:"មិថុនា",
    7:"កក្កដា",8:"សីហា",9:"កញ្ញា",10:"តុលា",11:"វិច្ឆិកា",12:"ធ្នូ"
}


# ── CSV exports ──────────────────────────────────────────────────

def export_workers_csv(workers):
    path = os.path.join(EXPORT_FOLDER, f"workers_{_ts()}.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Employee ID", "Full Name", "Department", "Position", "Phone",
                    "Salary", "Join Date", "Registered At", "Active"])
        for wk in workers:
            w.writerow([
                wk.get("employee_id",""), wk.get("full_name",""),
                wk.get("department",""), wk.get("position",""),
                wk.get("phone",""), wk.get("salary",""),
                wk.get("join_date",""), wk.get("registered_at",""),
                "Yes" if wk.get("is_active",1) else "No"
            ])
    return path


def export_leaves_csv(leaves):
    path = os.path.join(EXPORT_FOLDER, f"leaves_{_ts()}.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Employee ID", "Full Name", "Department",
                    "Leave Type", "Start Date", "End Date", "Days",
                    "Reason", "Status", "Admin Note", "Submitted At"])
        for r in leaves:
            try:
                days = (r["end_date"] - r["start_date"]).days + 1
            except Exception:
                days = ""
            w.writerow([
                r.get("id",""), r.get("employee_id",""), r.get("full_name",""),
                r.get("department",""),
                LEAVE_TYPE_KH.get(r.get("leave_type",""), r.get("leave_type","")),
                r.get("start_date",""), r.get("end_date",""), days,
                r.get("reason",""),
                STATUS_KH.get(r.get("status",""), r.get("status","")),
                r.get("admin_note",""), r.get("created_at","")
            ])
    return path


def export_payslips_csv(payslips):
    path = os.path.join(EXPORT_FOLDER, f"payslips_{_ts()}.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Employee ID", "Full Name", "Department", "Month", "Year", "Sent At"])
        for p in payslips:
            w.writerow([
                p.get("id",""), p.get("employee_id",""), p.get("full_name",""),
                p.get("department",""), p.get("month",""), p.get("year",""), p.get("sent_at","")
            ])
    return path


# ── PDF exports ──────────────────────────────────────────────────

def export_leaves_pdf(leaves, title="Leave Report"):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    path = os.path.join(EXPORT_FOLDER, f"leaves_{_ts()}.pdf")
    doc = SimpleDocTemplate(path, pagesize=landscape(A4),
                            leftMargin=1*cm, rightMargin=1*cm,
                            topMargin=1.5*cm, bottomMargin=1*cm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    elements.append(Spacer(1, 0.4*cm))

    headers = ["#", "Emp ID", "Name", "Dept", "Type", "Start", "End", "Days", "Status"]
    data = [headers]
    for r in leaves:
        try:
            days = (r["end_date"] - r["start_date"]).days + 1
        except Exception:
            days = "-"
        data.append([
            str(r.get("id","")),
            r.get("employee_id",""),
            r.get("full_name","")[:20],
            r.get("department","")[:15],
            r.get("leave_type","").capitalize(),
            str(r.get("start_date","")),
            str(r.get("end_date","")),
            str(days),
            r.get("status","").upper()
        ])

    col_widths = [1*cm, 2*cm, 4*cm, 3.5*cm, 3*cm, 2.5*cm, 2.5*cm, 1.5*cm, 2.5*cm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F2F3F4")]),
        ("GRID",       (0,0), (-1,-1), 0.4, colors.grey),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("PADDING",    (0,0), (-1,-1), 4),
    ]))
    elements.append(t)
    doc.build(elements)
    return path


def export_workers_pdf(workers, title="Employee Report"):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    path = os.path.join(EXPORT_FOLDER, f"workers_{_ts()}.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=1*cm, rightMargin=1*cm,
                            topMargin=1.5*cm, bottomMargin=1*cm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Paragraph(f"Total: {len(workers)} employees | {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    elements.append(Spacer(1, 0.4*cm))

    headers = ["Emp ID", "Full Name", "Department", "Position", "Phone"]
    data = [headers]
    for w in workers:
        data.append([
            w.get("employee_id",""),
            w.get("full_name","")[:25],
            w.get("department","")[:18],
            w.get("position","")[:18],
            w.get("phone",""),
        ])

    col_widths = [2.5*cm, 5*cm, 4*cm, 4*cm, 3.5*cm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1A5276")),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EBF5FB")]),
        ("GRID",       (0,0), (-1,-1), 0.4, colors.grey),
        ("ALIGN",      (0,0), (-1,-1), "LEFT"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("PADDING",    (0,0), (-1,-1), 5),
    ]))
    elements.append(t)
    doc.build(elements)
    return path


def _ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")
