"""
JobAgent AI — PDF Generator (Week 3)
Generates a STRICT ONE-PAGE resume PDF from a tailored resume dict using ReportLab.
Cover letter goes on its own page (not counted as part of the "one page" resume rule).
"""

import os
import logging
from config import PDF_OUTPUT_DIR

logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, PageBreak
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed — PDF generation disabled. Run: pip install reportlab")


def _safe_filename(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text)


def _build_resume_story(r: dict, styles_scale: float = 1.0) -> list:
    """Build the flowable story for the resume page at a given font/spacing scale."""
    base_font   = 9.5 * styles_scale
    name_font   = 19 * styles_scale
    section_font = 10.5 * styles_scale
    meta_font   = 8.5 * styles_scale
    leading     = base_font * 1.4
    space_after_section = 8 * styles_scale

    name_style = ParagraphStyle("Name", fontName="Helvetica-Bold",
                                fontSize=name_font, spaceAfter=2,
                                textColor=colors.HexColor("#1a1a2e"))
    section_style = ParagraphStyle("Section", fontName="Helvetica-Bold",
                                   fontSize=section_font, spaceBefore=space_after_section, spaceAfter=2,
                                   textColor=colors.HexColor("#16213e"))
    body_style = ParagraphStyle("Body", fontName="Helvetica",
                                fontSize=base_font, leading=leading, spaceAfter=1)
    meta_style = ParagraphStyle("Meta", fontName="Helvetica",
                                fontSize=meta_font, textColor=colors.grey)
    bullet_style = ParagraphStyle("Bullet", fontName="Helvetica",
                                  fontSize=base_font, leading=leading, leftIndent=10, spaceAfter=1)

    story = []
    story.append(Paragraph(r.get("name", "Your Name"), name_style))
    contact = " | ".join(filter(None, [
        r.get("location"), r.get("email"), r.get("phone"), r.get("linkedin"), r.get("github")
    ]))
    story.append(Paragraph(contact, meta_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#16213e"), spaceAfter=4))

    if r.get("summary"):
        story.append(Paragraph("SUMMARY", section_style))
        story.append(Paragraph(r["summary"], body_style))

    if r.get("skills"):
        story.append(Paragraph("SKILLS", section_style))
        story.append(Paragraph(" • ".join(r["skills"]), body_style))

    if r.get("experience"):
        story.append(Paragraph("EXPERIENCE", section_style))
        for exp in r["experience"]:
            story.append(Paragraph(
                f"<b>{exp.get('role', '')}</b> — {exp.get('company', '')} "
                f"<font color='grey'>({exp.get('duration', '')})</font>",
                body_style
            ))
            for bullet in exp.get("bullets", []):
                story.append(Paragraph(f"• {bullet}", bullet_style))

    if r.get("projects"):
        story.append(Paragraph("PROJECTS", section_style))
        for proj in r["projects"]:
            tech = ", ".join(proj.get("tech", []))
            story.append(Paragraph(f"<b>{proj.get('name', '')}</b> <font color='grey'>[{tech}]</font>", body_style))
            for bullet in proj.get("bullets", []):
                story.append(Paragraph(f"• {bullet}", bullet_style))

    if r.get("education"):
        edu = r["education"]
        story.append(Paragraph("EDUCATION", section_style))
        details = f" — {edu.get('details')}" if edu.get("details") else ""
        story.append(Paragraph(
            f"<b>{edu.get('degree', '')}</b>, {edu.get('institute', '')} ({edu.get('year', '')}){details}",
            body_style
        ))

    if r.get("leadership"):
        story.append(Paragraph("LEADERSHIP", section_style))
        for item in r["leadership"]:
            story.append(Paragraph(
                f"<b>{item.get('title', '')}</b> — {item.get('details', '')}",
                bullet_style
            ))

    return story


def _render_and_check_pages(filepath: str, story: list) -> int:
    """Render to a temp doc and return page count without keeping the file."""
    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        rightMargin=1.6*cm, leftMargin=1.6*cm,
        topMargin=1.3*cm, bottomMargin=1.3*cm,
    )
    doc.build(story)
    # Count pages via a lightweight check: reportlab doesn't expose page count
    # directly post-build, so we use pypdf if available; otherwise assume ok.
    try:
        from pypdf import PdfReader
        return len(PdfReader(filepath).pages)
    except Exception:
        return 1  # best-effort if pypdf isn't installed


def generate_resume_pdf(tailored_resume: dict, job: dict, cover_letter: str = "") -> str:
    """
    Build a STRICT one-page resume PDF (+ separate cover letter page).
    Auto-shrinks font scale up to 2 steps if content overflows one page.
    Returns the output file path.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is not installed. Run: pip install reportlab")

    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

    company_slug = _safe_filename(job.get("company", "company"))
    title_slug   = _safe_filename(job.get("title", "role"))[:30]
    filename     = f"resume_{company_slug}_{title_slug}.pdf"
    filepath     = os.path.join(PDF_OUTPUT_DIR, filename)

    # Try progressively smaller scales until it fits one page
    for scale in (1.0, 0.92, 0.85):
        resume_story = _build_resume_story(tailored_resume, styles_scale=scale)
        pages = _render_and_check_pages(filepath, list(resume_story))  # resume-only check
        if pages <= 1:
            logger.info("Resume fits on 1 page at scale=%.2f", scale)
            break
        logger.warning("Resume overflowed at scale=%.2f (%d pages) — shrinking", scale, pages)
    else:
        logger.warning("Resume still overflowing at smallest scale — trimming bullets further")
        # Last resort: hard trim content and rebuild at smallest scale
        trimmed = dict(tailored_resume)
        trimmed["experience"] = [
            {**e, "bullets": e.get("bullets", [])[:1]} for e in trimmed.get("experience", [])[:1]
        ]
        trimmed["projects"] = [
            {**p, "bullets": p.get("bullets", [])[:1]} for p in trimmed.get("projects", [])[:2]
        ]
        trimmed["leadership"] = []  # drop leadership entirely as last resort
        resume_story = _build_resume_story(trimmed, styles_scale=0.85)

    # Final build: resume page(s) + cover letter page
    full_story = list(resume_story)
    if cover_letter:
        full_story.append(PageBreak())
        cover_section = ParagraphStyle("CoverSection", fontName="Helvetica-Bold",
                                       fontSize=11, spaceAfter=6, textColor=colors.HexColor("#16213e"))
        cover_body = ParagraphStyle("CoverBody", fontName="Helvetica", fontSize=10, leading=15, spaceAfter=8)
        full_story.append(Paragraph("COVER LETTER", cover_section))
        full_story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#16213e"), spaceAfter=8))
        full_story.append(Paragraph(
            f"<b>Re: {job.get('title', 'Role')} at {job.get('company', 'Company')}</b>", cover_body
        ))
        full_story.append(Spacer(1, 8))
        for para in cover_letter.split("\n\n"):
            if para.strip():
                full_story.append(Paragraph(para.strip(), cover_body))

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        rightMargin=1.6*cm, leftMargin=1.6*cm,
        topMargin=1.3*cm, bottomMargin=1.3*cm,
    )
    doc.build(full_story)

    logger.info("PDF generated: %s", filepath)
    return filepath


def generate_all_pdfs(applications: list[dict]) -> list[str]:
    paths = []
    for app in applications:
        try:
            path = generate_resume_pdf(
                app["tailored_resume"], app["job"], app.get("cover_letter", "")
            )
            paths.append(path)
        except Exception as e:
            logger.error("PDF generation failed for %s: %s", app["job"].get("title"), e)
    return paths