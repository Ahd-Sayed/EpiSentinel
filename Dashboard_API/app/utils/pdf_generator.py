from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

def generate_pdf_bytes(cols, records, title):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(letter), 
        rightMargin=20, 
        leftMargin=20, 
        topMargin=20, 
        bottomMargin=20
    )
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="TitleStyle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=15,
        alignment=0
    )
    
    story.append(Paragraph(f"EpiGuard Africa — {title} Data Export", title_style))
    story.append(Spacer(1, 10))
    
    # Cap PDF records at 300 rows to ensure readability and PDF performance
    limited_records = records[:300]
    
    table_data = []
    # Header row
    table_data.append([str(c).upper() for c in cols])
    
    # Rows
    for r in limited_records:
        row = []
        for c in cols:
            # Match casing of keys
            key = c.upper() if c != "target_date" else c
            val = r.get(key, "")
            row.append(str(val))
        table_data.append(row)
        
    t = Table(table_data)
    
    # Style matrix matching dashboard color palettes
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1F2937")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#F9FAFB")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F3F4F6")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
        ('TOPPADDING', (0,1), (-1,-1), 4),
    ]))
    
    story.append(t)
    doc.build(story)
    return buffer.getvalue()
