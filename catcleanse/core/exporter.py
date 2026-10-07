"""Detailed portfolio validation report generation."""
from __future__ import annotations
from datetime import datetime, timezone
from io import BytesIO
import json


def build_validation_pdf(clean_df, summary, audit_entries):
    """Create a multi-page PDF with portfolio metrics, decisions, and cell evidence."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    navy = colors.HexColor("#1B2140")
    red = colors.HexColor("#D62828")
    pale = colors.HexColor("#F7F7FA")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallCell", parent=styles["BodyText"], fontName="Helvetica", fontSize=6.5, leading=8, alignment=TA_LEFT, spaceAfter=0))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=navy, spaceBefore=8, spaceAfter=5))
    styles["Title"].textColor = navy
    styles["Title"].fontSize = 22

    def safe(value):
        text = "" if value is None else str(value)
        return text.encode("cp1252", errors="replace").decode("cp1252")

    def cell(value):
        return Paragraph(safe(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>"), styles["SmallCell"])

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=12*mm, leftMargin=12*mm, topMargin=13*mm, bottomMargin=13*mm, title="CatCleanse Detailed Validation Report", author="CatCleanse AI")
    story = [Paragraph("CatCleanse AI | Exposure Validation Report", styles["Title"]),
             Paragraph("Kenya Re Exposure Standardizer · generated " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), styles["Normal"]),
             Spacer(1, 5*mm), Paragraph("Executive summary", styles["Section"])]
    summary_rows = [["Portfolio locations", f"{summary['portfolio_locations']:,}", "Building TIV", f"KES {summary['building_tiv_kes']:,.2f}"],
        ["Contents TIV", f"KES {summary['contents_tiv_kes']:,.2f}", "Average confidence", f"{summary['average_confidence']:.1%}"],
        ["Human review required", str(summary["requires_human_review"]), "Kenya coordinate coverage", f"{summary['coordinate_coverage']:,} / {summary['portfolio_locations']:,}"],
        ["Flood proximity flags", str(summary["high_flood_proximity"]), "Audit transformations", str(summary["audit_entry_count"])]]
    table = Table(summary_rows, colWidths=[42*mm, 47*mm, 48*mm, 55*mm])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),pale),("TEXTCOLOR",(0,0),(0,-1),navy),("TEXTCOLOR",(2,0),(2,-1),navy),("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D7D9E2")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("PADDING",(0,0),(-1,-1),5)]))
    story += [table, Spacer(1,4*mm), Paragraph("Validation interpretation",styles["Section"]),
        Paragraph("Confidence scores are deterministic screening scores, not calibrated probabilities. Records marked REQUIRES_HUMAN_REVIEW need analyst review before model handoff. Coordinates resolved from estate/sub-county centroids are approximate and are not rooftop geocodes.",styles["BodyText"]),
        Paragraph("Currency note: USD values are converted using the configured 130 KES/USD demo assumption. Confirm the portfolio policy FX rate before production use.",styles["BodyText"]),
        Paragraph("Flood proximity on cleansed records is a keyword/centroid screen, not a hydraulic hazard model. See the separate scenario model screen for the assumptions attached to proxy raster data.",styles["BodyText"]),
        Spacer(1,4*mm), Paragraph("OED location records",styles["Section"])]
    headers = ["LocNum","LocName","Latitude","Longitude","Geocode","Occupancy","Construction","Stories","Year built","Building TIV (KES)","Contents TIV (KES)","Confidence","Review","Flood flag"]
    rows = [[cell(x) for x in headers]]
    for _, row in clean_df.iterrows():
        rows.append([cell(row.get("LocNum")),cell(row.get("LocName")),cell(row.get("Latitude")),cell(row.get("Longitude")),cell(row.get("GeocodeQuality")),cell(row.get("OccupancyCode")),cell(row.get("ConstructionCode")),cell(row.get("NumberOfStories")),cell(row.get("YearBuilt")),cell(f"{float(row.get('BuildingTIV') or 0):,.0f}"),cell(f"{float(row.get('ContentsTIV') or 0):,.0f}"),cell(f"{float(row.get('ConfidenceScore') or 0):.0%}"),cell(row.get("ReviewStatus")),cell(row.get("High_Flood_Proximity_Flag"))])
    widths=[11*mm,29*mm,17*mm,17*mm,18*mm,17*mm,18*mm,10*mm,12*mm,23*mm,23*mm,14*mm,29*mm,12*mm]
    location_table=Table(rows,colWidths=widths,repeatRows=1)
    location_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),navy),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#D7D9E2")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,pale]),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]))
    story += [location_table, PageBreak(), Paragraph("Field-level audit trail",styles["Section"]),
        Paragraph("Each row records the raw value, normalized value, transformation method, source evidence, and rationale captured during cleansing.",styles["BodyText"]),Spacer(1,3*mm)]
    audit_rows=[[cell(x) for x in ["LocNum","Location","Field","Raw value","Cleaned value","Method","Evidence","Rationale"]]]
    for item in audit_entries:
        audit_rows.append([cell(item.get("LocNum")),cell(item.get("LocName")),cell(item.get("field")),cell(item.get("raw_value")),cell(item.get("cleaned_value")),cell(item.get("transformation_type")),cell(item.get("evidence")),cell(item.get("rationale"))])
    if len(audit_rows)==1:
        audit_rows.append([cell("—"),cell("—"),cell("No transformations"),cell("—"),cell("—"),cell("—"),cell("—"),cell("No field changes were recorded.")])
    audit_table=Table(audit_rows,colWidths=[13*mm,26*mm,23*mm,34*mm,30*mm,28*mm,53*mm,65*mm],repeatRows=1)
    audit_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),navy),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#D7D9E2")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,pale]),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]))
    story.append(audit_table)
    doc.build(story)
    return buffer.getvalue()
