"""Render a sanitized complaint document to PDF.

Consumes only `ComplaintDocument`, never a database row, so nothing unsanitized
can reach the output. Fonts are embedded and subset by fpdf2, and text shaping is
enabled so Devanagari conjuncts and matras render correctly rather than as
disconnected glyphs.
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.services.complaint_document_service import ComplaintDocument

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
NAVY = (11, 55, 104)
INK = (23, 50, 79)
MUTED = (90, 106, 124)
RULE = (206, 217, 229)
WARN_BG = (255, 247, 232)
WARN_INK = (122, 74, 12)

DISCLAIMER = (
    "This is a citizen-generated copy of a complaint recorded in the CyberRakshak "
    "prototype. It is NOT an FIR, NOT a police or government acknowledgement, and NOT "
    "proof that this complaint was submitted to any authority. CyberRakshak is not "
    "connected to police, government, banking or telecom systems."
)


class ComplaintCopyPDF(FPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("body", size=8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, "CyberRakshak - citizen complaint copy (prototype)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*RULE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("body", size=8)
        self.set_text_color(*MUTED)
        self.cell(0, 5, f"Page {self.page_no()} of {{nb}}", align="C")


def _register_fonts(pdf: FPDF) -> None:
    pdf.add_font("body", "", str(FONT_DIR / "NotoSans-Regular.ttf"))
    pdf.add_font("body", "B", str(FONT_DIR / "NotoSans-Bold.ttf"))
    pdf.add_font("deva", "", str(FONT_DIR / "NotoSansDevanagari-Regular.ttf"))
    pdf.add_font("deva", "B", str(FONT_DIR / "NotoSansDevanagari-Bold.ttf"))
    # Latin first, Devanagari as fallback: one document can mix both scripts.
    pdf.set_fallback_fonts(["deva"])
    try:
        pdf.set_text_shaping(True)
    except Exception:  # noqa: BLE001 - shaping needs uharfbuzz; degrade rather than fail
        pass


def render_complaint_copy(document: ComplaintDocument) -> bytes:
    pdf = ComplaintCopyPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(16, 14, 16)
    _register_fonts(pdf)
    pdf.set_title(f"CyberRakshak complaint copy {document.complaint_number}")
    pdf.set_author("CyberRakshak prototype")
    pdf.add_page()

    usable = pdf.w - pdf.l_margin - pdf.r_margin

    # Masthead
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("body", "B", 15)
    pdf.cell(usable, 11, "CyberRakshak", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.set_font("body", size=9)
    pdf.cell(usable, 7, "Citizen complaint copy - prototype record", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.ln(4)

    # Disclaimer, deliberately above the content rather than in a footnote.
    pdf.set_fill_color(*WARN_BG)
    pdf.set_text_color(*WARN_INK)
    pdf.set_font("body", "B", 9)
    pdf.multi_cell(usable, 5, "Please read", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.set_font("body", size=8.5)
    pdf.multi_cell(usable, 4.6, DISCLAIMER, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.ln(4)

    for section in document.sections:
        _render_section(pdf, section, usable)

    pdf.ln(2)
    pdf.set_draw_color(*RULE)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("body", size=8)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        usable,
        4.4,
        f"Generated {document.generated_at.strftime('%d %b %Y, %H:%M UTC')} - document version {document.document_version} - reporting mode {document.reporting_mode}.",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    return bytes(pdf.output())


def _render_section(pdf: FPDF, section, usable: float) -> None:
    # Keep a heading with at least some of its content rather than orphaning it.
    if pdf.will_page_break(22):
        pdf.add_page()

    pdf.set_text_color(*NAVY)
    pdf.set_font("body", "B", 11)
    pdf.multi_cell(usable, 6.5, section.title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*RULE)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)

    label_width = min(58.0, usable * 0.38)
    for item in section.fields:
        pdf.set_font("body", "B", 9)
        pdf.set_text_color(*MUTED)
        start_y = pdf.get_y()
        pdf.multi_cell(label_width, 5, item.label, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("body", size=9.5)
        pdf.set_text_color(*INK)
        pdf.set_xy(pdf.l_margin + label_width, start_y)
        # Long identifiers and URLs must wrap inside the column, never overflow it.
        pdf.multi_cell(usable - label_width, 5, item.value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(0.6)

    for paragraph in section.paragraphs:
        pdf.set_font("body", size=9.5)
        pdf.set_text_color(*INK)
        pdf.multi_cell(usable, 5, paragraph, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1.4)

    if section.note:
        pdf.set_font("body", size=8.5)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(usable, 4.4, section.note, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(3)
