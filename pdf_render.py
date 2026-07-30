"""
Skyline Site Assessment — PDF renderer
========================================
Primary: WeasyPrint (HTML/CSS -> PDF), matches the Skyline brand system.
Fallback: pure-Python reportlab renderer if WeasyPrint's system libs are
unavailable in the deploy environment (some Render images lack libpango/
libcairo). Whichever succeeds is used; the public API `render_pdf()` is
identical either way.
"""

import os
import base64
import html as htmlmod
from datetime import datetime

import schemas

GOLD = "#E8B84B"
DARK = "#111111"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


def _fmt_value(field: dict, value) -> str:
    ftype = field.get("type")
    unit = field.get("unit")
    if value is None or value == "" or (isinstance(value, list) and not value):
        return "—"
    if ftype == "yesno":
        if isinstance(value, bool):
            return "Yes" if value else "No"
        v = str(value).strip().lower()
        if v in ("yes", "true", "1"):
            return "Yes"
        if v in ("no", "false", "0"):
            return "No"
        return "—"
    if ftype == "multiselect":
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)
    if ftype in ("number",) and unit:
        return f"{value} {unit}"
    return str(value)


def _service_and_sections(assessment: dict):
    service = schemas.SERVICE_BY_ID.get(assessment["service_id"])
    if not service:
        return None, []
    return service, service.get("sections", [])


def _build_html(assessment: dict, upload_dir: str) -> str:
    service, sections = _service_and_sections(assessment)
    service_name = service["name"] if service else assessment["service_id"]
    data = assessment.get("data") or {}
    property_name = data.get("property_name") or assessment.get("property_name") or "Untitled Property"
    today = datetime.now().strftime("%d %B %Y")
    aid = assessment.get("id")

    sections_html = []
    for section in sections:
        rows = []
        for field in section.get("fields", []):
            val = data.get(field["key"])
            display = _fmt_value(field, val)
            if field.get("type") == "multiselect" and isinstance(val, list) and val:
                items = "".join(f"<li>{htmlmod.escape(str(v))}</li>" for v in val)
                display_html = f"<ul class='ms'>{items}</ul>"
            else:
                display_html = htmlmod.escape(display).replace("\n", "<br/>")
            rows.append(
                f"<tr><td class='q'>{htmlmod.escape(field['label'])}</td>"
                f"<td class='a'>{display_html}</td></tr>"
            )
        desc = f"<p class='sec-desc'>{htmlmod.escape(section.get('description',''))}</p>" if section.get("description") else ""
        sections_html.append(
            f"""
            <div class="section">
              <h2>{htmlmod.escape(section['title'])}</h2>
              <div class="rule"></div>
              {desc}
              <table class="qa">{''.join(rows)}</table>
            </div>
            """
        )

    # Attachment thumbnails (images only, skip videos)
    attachments = assessment.get("attachments") or []
    thumbs = []
    for a in attachments:
        mime = (a.get("mime_type") or "").lower()
        name = (a.get("filename") or "")
        ext = os.path.splitext(name)[1].lower()
        is_image = mime.startswith("image/") or ext in IMAGE_EXTS
        if not is_image:
            continue
        path = os.path.join(upload_dir, str(aid), name)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            mtype = mime or "image/jpeg"
            caption = htmlmod.escape(a.get("caption") or a.get("original_name") or "")
            thumbs.append(
                f"<figure><img src='data:{mtype};base64,{b64}'/><figcaption>{caption}</figcaption></figure>"
            )
        except Exception:
            continue

    attachments_html = ""
    if thumbs:
        attachments_html = f"""
        <div class="section">
          <h2>Attachments</h2>
          <div class="rule"></div>
          <div class="thumbs">{''.join(thumbs)}</div>
        </div>
        """

    logo_path = os.path.join(os.path.dirname(__file__), "static", "img", "skyline-logo.png")
    logo_b64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("ascii")

    html_doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      @page {{
        size: A4;
        margin: 2.2cm 1.6cm 2.4cm 1.6cm;
        @top-left {{ content: "SKYLINE DRONES — Site Assessment"; font-family: 'Carlito', sans-serif; font-size: 9pt; color: #666; }}
        @bottom-center {{ content: "Page " counter(page) " of " counter(pages); font-family: 'Carlito', sans-serif; font-size: 9pt; color: #888; }}
      }}
      * {{ box-sizing: border-box; }}
      body {{ font-family: 'Carlito', 'Helvetica', sans-serif; color: {DARK}; font-size: 10.5pt; line-height: 1.45; }}
      .header {{ display: flex; align-items: center; gap: 14px; border-bottom: 3px solid {GOLD}; padding-bottom: 12px; margin-bottom: 18px; }}
      .header img {{ height: 46px; }}
      .header .title-block {{ flex: 1; }}
      .title-block h1 {{ font-family: 'Archivo Black', sans-serif; font-size: 20pt; margin: 0 0 2px 0; text-transform: uppercase; letter-spacing: 0.5px; }}
      .title-block .sub {{ font-size: 11pt; color: #444; margin: 0; }}
      .title-block .meta {{ font-size: 9pt; color: #888; margin-top: 4px; }}
      .section {{ margin-bottom: 20px; page-break-inside: avoid; }}
      .section h2 {{ font-family: 'Archivo Black', sans-serif; font-size: 13pt; margin: 0 0 4px 0; text-transform: uppercase; }}
      .rule {{ height: 3px; width: 60px; background: {GOLD}; margin-bottom: 8px; }}
      .sec-desc {{ font-size: 9.5pt; color: #666; margin: 0 0 8px 0; font-style: italic; }}
      table.qa {{ width: 100%; border-collapse: collapse; }}
      table.qa tr {{ border-bottom: 1px solid #eee; }}
      table.qa td {{ padding: 6px 4px; vertical-align: top; }}
      table.qa td.q {{ width: 42%; font-weight: bold; color: #333; padding-right: 12px; }}
      table.qa td.a {{ width: 58%; color: #111; }}
      ul.ms {{ margin: 0; padding-left: 16px; }}
      .thumbs {{ display: flex; flex-wrap: wrap; gap: 10px; }}
      .thumbs figure {{ width: 30%; margin: 0; }}
      .thumbs img {{ width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
      .thumbs figcaption {{ font-size: 8pt; color: #777; text-align: center; margin-top: 2px; }}
    </style>
    </head>
    <body>
      <div class="header">
        {"<img src='data:image/png;base64," + logo_b64 + "'/>" if logo_b64 else ""}
        <div class="title-block">
          <h1>{htmlmod.escape(service_name)}</h1>
          <p class="sub">{htmlmod.escape(property_name)}</p>
          <p class="meta">Site Assessment #{aid} &middot; Generated {today} &middot; Assessor: {htmlmod.escape(assessment.get('assessor') or 'Brice Adler')}</p>
        </div>
      </div>
      {''.join(sections_html)}
      {attachments_html}
    </body>
    </html>
    """
    return html_doc


def _render_with_weasyprint(assessment: dict, upload_dir: str) -> bytes:
    from weasyprint import HTML
    html_doc = _build_html(assessment, upload_dir)
    return HTML(string=html_doc).write_pdf()


def _render_with_reportlab(assessment: dict, upload_dir: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, ListFlowable, ListItem
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    import io as _io

    service, sections = _service_and_sections(assessment)
    service_name = service["name"] if service else assessment["service_id"]
    data = assessment.get("data") or {}
    property_name = data.get("property_name") or assessment.get("property_name") or "Untitled Property"
    aid = assessment.get("id")
    today = datetime.now().strftime("%d %B %Y")

    buf = _io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2.2 * cm, bottomMargin=2.2 * cm,
                             leftMargin=1.6 * cm, rightMargin=1.6 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("SkylineTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                                  fontSize=20, textColor=HexColor(DARK), spaceAfter=2)
    sub_style = ParagraphStyle("SkylineSub", parent=styles["Normal"], fontSize=11, textColor=HexColor("#444444"))
    meta_style = ParagraphStyle("SkylineMeta", parent=styles["Normal"], fontSize=8.5, textColor=HexColor("#888888"), spaceAfter=10)
    h2_style = ParagraphStyle("SkylineH2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                               fontSize=13, textColor=HexColor(DARK), spaceBefore=14, spaceAfter=4)
    desc_style = ParagraphStyle("SkylineDesc", parent=styles["Normal"], fontSize=9, textColor=HexColor("#666666"), spaceAfter=6)
    q_style = ParagraphStyle("Q", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5)
    a_style = ParagraphStyle("A", parent=styles["Normal"], fontSize=9.5)

    story = []

    logo_path = os.path.join(os.path.dirname(__file__), "static", "img", "skyline-logo.png")
    header_cells = []
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=3.2 * cm, height=1.4 * cm, kind="proportional")
            header_cells.append(img)
        except Exception:
            pass
    title_block = [
        Paragraph(service_name.upper(), title_style),
        Paragraph(property_name, sub_style),
        Paragraph(
            f"Site Assessment #{aid} &middot; Generated {today} &middot; Assessor: {assessment.get('assessor') or 'Brice Adler'}",
            meta_style,
        ),
    ]
    if header_cells:
        header_table = Table([[header_cells[0], title_block]], colWidths=[3.5 * cm, None])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 3, HexColor(GOLD)),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(header_table)
    else:
        story.extend(title_block)
    story.append(Spacer(1, 10))

    for section in sections:
        story.append(Paragraph(section["title"].upper(), h2_style))
        if section.get("description"):
            story.append(Paragraph(section["description"], desc_style))
        rows = []
        for field in section.get("fields", []):
            val = data.get(field["key"])
            display = _fmt_value(field, val)
            if field.get("type") == "multiselect" and isinstance(val, list) and val:
                items = [ListItem(Paragraph(str(v), a_style)) for v in val]
                a_cell = ListFlowable(items, bulletType="bullet", leftIndent=10)
            else:
                a_cell = Paragraph(display.replace("\n", "<br/>"), a_style)
            rows.append([Paragraph(field["label"], q_style), a_cell])
        if rows:
            t = Table(rows, colWidths=[7.2 * cm, 9.4 * cm])
            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#eeeeee")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t)

    # Attachments (images only)
    attachments = assessment.get("attachments") or []
    image_flowables = []
    for a in attachments:
        mime = (a.get("mime_type") or "").lower()
        name = a.get("filename") or ""
        ext = os.path.splitext(name)[1].lower()
        is_image = mime.startswith("image/") or ext in IMAGE_EXTS
        if not is_image:
            continue
        path = os.path.join(upload_dir, str(aid), name)
        if not os.path.exists(path):
            continue
        try:
            img = Image(path, width=5.5 * cm, height=4 * cm, kind="proportional")
            image_flowables.append(img)
        except Exception:
            continue
    if image_flowables:
        story.append(Paragraph("ATTACHMENTS", h2_style))
        # lay out 3 per row
        grid_rows = []
        for i in range(0, len(image_flowables), 3):
            grid_rows.append(image_flowables[i:i + 3])
        for r in grid_rows:
            while len(r) < 3:
                r.append("")
            t = Table([r], colWidths=[5.7 * cm] * 3)
            story.append(t)

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(HexColor("#888888"))
        canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"Page {doc_.page}")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(1.6 * cm, A4[1] - 1.4 * cm, "SKYLINE DRONES — Site Assessment")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def render_pdf(assessment: dict, upload_dir: str) -> bytes:
    """Render the assessment to PDF bytes. Tries WeasyPrint, falls back to reportlab."""
    try:
        return _render_with_weasyprint(assessment, upload_dir)
    except Exception as e:
        import logging
        logging.getLogger("skyline-site-assessment").warning(
            f"WeasyPrint unavailable/failed ({e}); falling back to reportlab"
        )
        return _render_with_reportlab(assessment, upload_dir)
