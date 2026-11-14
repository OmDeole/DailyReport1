import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from ..models import CommentRecord

def export_comments_to_excel_bytes():
    """
    Generates the Critical_FG_Comments_Log.xlsx workbook from PostgreSQL records.
    Returns bytes suitable for an HttpResponse.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Comments"
    ws.views.sheetView[0].showGridLines = True

    headers = [
        ("ID", 8),
        ("Created", 20),
        ("Last Updated", 20),
        ("Part Number", 15),
        ("Description", 30),
        ("Customer", 18),
        ("Minifactory", 16),
        ("Line", 14),
        ("Stakeholder", 18),
        ("Issue Category", 18),
        ("Stakeholder Input / Discussion", 50),
        ("Action Being Taken", 50),
        ("Owner", 16),
        ("Target Date", 14),
        ("Status", 12),
        ("Control Status", 15),
        ("Needs Escalation", 16),
        ("Escalation Details", 36),
        ("Plan Value (INR) at entry", 20),
        ("Pending Value (INR) at entry", 20),
    ]

    header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="E5E7EB"),
        right=Side(style="thin", color="E5E7EB"),
        top=Side(style="thin", color="E5E7EB"),
        bottom=Side(style="thin", color="E5E7EB"),
    )

    # Write Headers
    for col_idx, (header_text, width) in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        col_letter = ws.cell(row=1, column=col_idx).column_letter
        ws.column_dimensions[col_letter].width = width

    ws.row_dimensions[1].height = 28

    comments = CommentRecord.objects.all().order_by("-updated_at")
    for row_idx, c in enumerate(comments, 2):
        row_vals = [
            c.comment_id,
            c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
            c.updated_at.strftime("%Y-%m-%d %H:%M:%S") if c.updated_at else "",
            c.part,
            c.desc,
            c.customer,
            c.minifactory,
            c.line,
            c.stakeholder,
            c.category,
            c.discussion,
            c.action,
            c.owner,
            c.target_date,
            c.status,
            c.criticality,
            c.needs_escalation,
            c.escalation_details,
            c.plan_val,
            c.pending_val,
        ]
        for col_idx, val in enumerate(row_vals, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = Font(name="Segoe UI", size=9)
            cell.border = thin_border
            cell.alignment = align_center if col_idx in [1, 2, 3, 13, 14, 15, 16, 17] else align_left
        ws.row_dimensions[row_idx].height = 22

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()

