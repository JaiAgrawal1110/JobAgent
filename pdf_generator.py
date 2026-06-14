"""
JobAgent AI — PDF Generator (Week 3)
Generates a formatted resume PDF from a tailored resume dict using ReportLab.
"""

import os
import logging
from datetime import datetime
from config import PDF_OUTPUT_DIR

logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed — PDF generation disabled. Run: pip install reportlab")


def _safe_filename(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text)


def generate_resume_pdf(tailored_resume: dict, job: dict, cover_letter: str = "") -> str:
    """
    Build a PDF resume + cover letter for one job.
    Returns the output file path.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is not installed. Run: pip install reportlab")

    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

    company_slug = _safe_filename(job.get("company", "company"))
    title_slug   = _safe_filename(job.get("title", "role"))[:30]
    filename     = f"resume_{company_slug}_{title_slug}.pdf"
    filepath     = os.path.join(PDF_OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    story  = []

    # ---- Custom styles ----
    name_style = ParagraphStyle("Name", parent=styles["Title"],
                                fontSize=20, spaceAfter=2, textColor=colors.HexColor("#1a1a2e"))
    section_style = ParagraphStyle("Section", parent=styles["Heading2"],
                                   fontSize=11, spaceBefore=10, spaceAfter=2,
                                   textColor=colors.HexColor("#16213e"), borderPadding=(0,0,2,0))
    body_style = ParagraphStyle("Body", parent=styles["Normal"],
                                fontSize=9.5, leading=14, spaceAfter=2)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"],
                                fontSize=9, textColor=colors.grey)
    bullet_style = ParagraphStyle("Bullet", parent=styles["Normal"],
                                  fontSize=9.5, leading=13, leftIndent=12)

    r = tailored_resume

    # ---- Header ----
    story.append(Paragraph(r.get("name", "Your Name"), name_style))
    contact = " · ".join(filter(None, [
        r.get("email"), r.get("phone"), r.get("linkedin"), r.get("github")
    ]))
    story.append(Paragraph(contact, meta_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#16213e"), spaceAfter=6))

    # ---- Summary ----
    if r.get("summary"):
        story.append(Paragraph("SUMMARY", section_style))
        story.append(Paragraph(r["summary"], body_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))

    # ---- Skills ----
    if r.get("skills"):
        story.append(Paragraph("SKILLS", section_style))
        skills_text = " · ".join(r["skills"])
        story.append(Paragraph(skills_text, body_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))

    # ---- Experience ----
    if r.get("experience"):
        story.append(Paragraph("EXPERIENCE", section_style))
        for exp in r["experience"]:
            story.append(Paragraph(
                f"<b>{exp.get('role', '')}</b> — {exp.get('company', '')} <font color='grey'>({exp.get('duration', '')})</font>",
                body_style
            ))
            for bullet in exp.get("bullets", []):
                story.append(Paragraph(f"• {bullet}", bullet_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))

    # ---- Projects ----
    if r.get("projects"):
        story.append(Paragraph("PROJECTS", section_style))
        for proj in r["projects"]:
            tech = ", ".join(proj.get("tech", []))
            story.append(Paragraph(
                f"<b>{proj.get('name', '')}</b> <font color='grey'>[{tech}]</font>",
                body_style
            ))
            story.append(Paragraph(proj.get("description", ""), bullet_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))

    # ---- Education ----
    if r.get("education"):
        edu = r["education"]
        story.append(Paragraph("EDUCATION", section_style))
        story.append(Paragraph(
            f"<b>{edu.get('degree', '')}</b> — {edu.get('institute', '')} ({edu.get('year', '')})",
            body_style
        ))

    # ---- Cover Letter (second page) ----
    if cover_letter:
        from reportlab.platypus import PageBreak
        story.append(PageBreak())
        story.append(Paragraph("COVER LETTER", section_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#16213e"), spaceAfter=8))
        story.append(Paragraph(f"<b>Re: {job.get('title', 'Role')} at {job.get('company', 'Company')}</b>", body_style))
        story.append(Spacer(1, 8))
        for para in cover_letter.split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), body_style))
                story.append(Spacer(1, 6))

    doc.build(story)
    logger.info("PDF generated: %s", filepath)
    return filepath


def generate_all_pdfs(applications: list[dict]) -> list[str]:
    """Generate PDFs for a list of application dicts (from tailor.prepare_application)."""
    paths = []
    for app in applications:
        try:
            path = generate_resume_pdf(
                app["tailored_resume"],
                app["job"],
                app.get("cover_letter", "")
            )
            paths.append(path)
        except Exception as e:
            logger.error("PDF generation failed for %s: %s", app["job"].get("title"), e)
    return paths
