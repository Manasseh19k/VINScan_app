from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io

def generate_report_pdf(report: dict, dealer_brand: dict = None) -> bytes:
    brand_name = dealer_brand or {'name': 'VINScan', 'color': '#185FA5'}
    vehicle = report.get('vehicle', {})
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch
    )
    brand_color = _hex_to_color(brand_name['color'])
    story = []
    styles = getSampleStyleSheet()
    
    # Header
    story.append(Paragraph(
        f"<font color='{brand_name.get('color', '#185FA5')}'><b>{brand_name['name']}</b></font>",
        ParagraphStyle('BrandName', fontSize=20, leading=24)
    ))
    story.append(Paragraph(
        "Vehicle History Report",
        ParagraphStyle('SubTitle', fontSize=11, textColor=colors.grey)
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=brand_color, spaceAfter=12))
    
    # Vehicle Information
    car_name = f"{vehicle.get('year','')} {vehicle.get('make','')} " \
               f"{vehicle.get('model','')} {vehicle.get('trim','')}"
    story.append(Paragraph(
        f"<b>{car_name.strip() or 'Unknown Vehicle'}</b>",
        ParagraphStyle('CarName', fontSize=15, leading=20)
    ))
    story.append(Paragraph(
        f"VIN: {report.get('vin', '—')}",
        ParagraphStyle('VIN', fontSize=10, textColor=colors.grey,
                       fontName='Courier', spaceAfter=12)
    ))
    
    # Score and Summary
    score = report.get('risk_score', 0)
    score_color = (colors.HexColor('#0F6E56') if score >= 70
                   else colors.HexColor('#BA7517') if score >= 40
                   else colors.HexColor('#A32D2D'))
    score_label = 'Good' if score >= 70 else 'Fair' if score >= 40 else 'Poor'

    score_table = Table(
        [[Paragraph(f"<b>{score}</b>", ParagraphStyle('ScoreNum', fontSize=28,
            textColor=score_color, alignment=TA_CENTER)),
          Paragraph(f"Buy Confidence Score<br/><font color='{_color_to_hex(score_color)}'>"
                    f"<b>{score_label}</b></font>",
                    ParagraphStyle('ScoreLbl', fontSize=11, leading=16,
                                   textColor=colors.grey, alignment=TA_LEFT))]],
        colWidths=[1.2 * inch, 4 * inch],
    )
    score_table.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW',   (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 12))
    
    def section(title: str):
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            title.upper(),
            ParagraphStyle('SectionTitle', fontSize=10, textColor=colors.grey,
                           spaceAfter=6, SpaceAfter=6, letterSpacing=0.8)
        ))
    
    def data_row(label: str, value: str, tag_color=None):
        val_para = Paragraph(
            f"<font color='{tag_color or '#222222'}'><b>{value}</b></font>",
            ParagraphStyle('Val', fontSize=10, alignment=TA_LEFT)
        )
        row_table = Table(
            [[Paragraph(label, ParagraphStyle('Lbl', fontSize=10,
                        textColor=colors.HexColor('#555555'))), val_para]],
            colWidths=[3.5 * inch, 2.5 * inch],
        )
        row_table.setStyle(TableStyle([
            ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW',    (0, 0), (-1, -1), 0.5, colors.HexColor('#eeeeee')),
            ('TOPPADDING',   (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
        ]))
        story.append(row_table)
        
    # Accidents & Damage
    section("Accidents & Damage History")
    accidents = report.get('accidents', [])
    if accidents:
        for acc in accidents:
            sev   = a.get('severity', 'Minor')
            color = ('#A32D2D' if 'severe' in sev.lower()
                     else '#BA7517' if 'moderate' in sev.lower() else '#555555')
            parts = [f"{sev} — {a.get('date', 'Date unknown')}"]
            if a.get('type'):    parts.append(a['type'])
            if a.get('state'):   parts.append(f"State: {a['state']}")
            if a.get('odometer'):parts.append(f"At {a['odometer']:,} miles")
            if a.get('airbag_deployed'): parts.append("⚠ Airbags deployed")
            story.append(Paragraph(
                "  ·  ".join(parts),
                ParagraphStyle('AccRow', fontSize=10, textColor=colors.HexColor(color),
                               leftIndent=8, spaceAfter=4,
                               backColor=colors.HexColor('#fafafa'))
            ))
    else:
        data_row("No accidents on record", "Clean ✓", '#0F6E56')
    
    # Ownership History
    section("Ownership History")
    data_row("Number of Previous Owners", str(report.get('owner_count', '—')))
    for i, o in enumerate(report.get('owners', []), 1):
        label = f"Owner {i}"
        value = f"{o.get('entity_type','Private')} · {o.get('state','—')}"
        if o.get('acquired'): value += f" ({o['acquired']}–{o.get('sold','present')})"
        data_row(label, value)

    # ── Title ───────────────────────────────────────────────────────
    section("Title Status")
    flags = report.get('title_flags', [])
    if flags:
        data_row("Title flags", ", ".join(flags).title(), '#A32D2D')
    else:
        data_row("Title status", "Clean ✓", '#0F6E56')
    if report.get('last_reported_odometer'):
        data_row("Last reported mileage",
                 f"{report['last_reported_odometer']:,} mi")
    
    # Title History
    section("Title Status History")
    flags = report.get('title_history', [])
    if flags:
        data_row("Title events", ", ".join(flags).title(), '#A32D2D')
    else:
        data_row("Title history", "Clean ✓", '#0F6E56')
    if report.get('last_reported_odometer'):
        data_row("Last reported mileage",
                 f"{report['last_reported_odometer']:,} mi")
    
    # Recalls
    section("Safety Recalls")
    recalls = report.get('recalls', [])
    if recalls:
        for r in recalls:
            data_row(r.get('Component', 'Unknown Component'),
                     f"Recall #{r.get('id', '--')}", '#AD322D')
    else:
        data_row("No safety recalls", "None ✓", '#0F6E56')
    
    
    # Market Value
    market_value = report.get('market_value') or {}
    if market_value.get('fair'):
        section("Estimated Market Value")
        data_row("Fair Market Value", f"${market_value['fair']:,} ({market_value.get('source', 'VINAudit')})")
        if market_value.get('low') and market_value.get('high'):
            data_row("Value Range",
                     f"${market_value['low']:,} - ${market_value['high']:,}",
                     '#555555')
    
    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5,
                            color=colors.lightgrey, spaceAfter=8))
    story.append(Paragraph(
        f"Report generated by {brand_name['name']}  ·  Data: NHTSA, VINAudit  ·  "
        "For informational purposes only.",
        ParagraphStyle('Footer', fontSize=8, textColor=colors.grey,
                       alignment=TA_CENTER)
    ))
    
    doc.build(story)
    return buffer.getvalue()
    

def _hex_to_color(hex_str: str) -> colors.Color:
    return colors.HexColor(hex_str)


def _color_to_hex(color: colors.Color) -> str:
    return f"#{int(color.red*255):02x}{int(color.green*255):02x}{int(color.blue*255):02x}"