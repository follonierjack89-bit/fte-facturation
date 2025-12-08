from datetime import datetime
from pathlib import Path
from typing import Optional

import qrcode
from fpdf import FPDF

from app.logic.models import Invoice, Settings
from app.qr.swiss_qr import build_payload

FACTURE_DIR = Path("Factures")
FACTURE_DIR.mkdir(exist_ok=True)


class InvoicePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "Facture", ln=True, align="R")

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.cell(0, 10, f"Généré le {datetime.now().strftime('%d.%m.%Y %H:%M')}", align="C")


def format_address(lines):
    return "\n".join(lines)


def generate_invoice_pdf(invoice: Invoice, settings: Settings, logo_path: Optional[str] = None) -> Path:
    pdf = InvoicePDF()
    pdf.add_page()

    if logo_path and Path(logo_path).exists():
        pdf.image(logo_path, x=10, y=10, w=30)
        pdf.set_xy(10, 40)
    else:
        pdf.set_xy(10, 20)

    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(80, 6, format_address([
        settings.company_name,
        settings.street,
        f"{settings.zip_code} {settings.city}",
        settings.country,
    ]))

    pdf.set_xy(120, 30)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(80, 6, format_address([
        invoice.client.company,
        invoice.client.street,
        f"{invoice.client.zip_code} {invoice.client.city}",
        invoice.client.country,
    ]))

    pdf.ln(10)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Facture n° {invoice.number} - Date: {invoice.invoice_date.strftime('%d.%m.%Y')}", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(80, 8, "Description", border=1)
    pdf.cell(25, 8, "Qté", border=1, align="R")
    pdf.cell(30, 8, "Prix", border=1, align="R")
    pdf.cell(30, 8, "Total", border=1, align="R", ln=True)

    pdf.set_font("Helvetica", size=11)
    for line in invoice.lines:
        pdf.cell(80, 8, line.description, border=1)
        pdf.cell(25, 8, f"{line.quantity:.2f}", border=1, align="R")
        pdf.cell(30, 8, f"{line.unit_price:.2f}", border=1, align="R")
        pdf.cell(30, 8, f"{line.total:.2f}", border=1, align="R", ln=True)

    pdf.cell(0, 8, "", ln=True)
    pdf.cell(135)
    pdf.cell(30, 8, "Sous-total", border=1)
    pdf.cell(30, 8, f"{invoice.subtotal:.2f} CHF", border=1, ln=True)
    pdf.cell(135)
    pdf.cell(30, 8, "TVA", border=1)
    pdf.cell(30, 8, f"{invoice.vat_amount:.2f} CHF", border=1, ln=True)
    pdf.cell(135)
    pdf.cell(30, 8, "Total", border=1)
    pdf.cell(30, 8, f"{invoice.total:.2f} CHF", border=1, ln=True)

    if invoice.notes:
        pdf.ln(6)
        pdf.multi_cell(0, 8, f"Conditions / notes :\n{invoice.notes}")

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Section QR-facture", ln=True)
    payload = build_payload(invoice, settings)
    qr_text = payload.to_text()
    qr_temp_path = Path(__file__).resolve().parent / "qr_temp.png"
    qr_image = qrcode.make(qr_text)
    qr_image.save(qr_temp_path)
    pdf.image(str(qr_temp_path), x=10, y=30, w=60, h=60)

    pdf.set_xy(80, 30)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 7, format_address([
        "Compte QR-IBAN : " + settings.qr_iban,
        "Bénéficiaire :",
        settings.company_name,
        settings.street,
        f"{settings.zip_code} {settings.city}",
        settings.country,
        "",
        "Montant : {:.2f} CHF".format(invoice.total),
        "Payer depuis :",
        invoice.client.company,
        invoice.client.street,
        f"{invoice.client.zip_code} {invoice.client.city}",
        invoice.client.country,
    ]))

    filename = FACTURE_DIR / f"Facture_{invoice.number}_{invoice.client.company.replace(' ', '_')}.pdf"
    pdf.output(str(filename))
    try:
        qr_temp_path.unlink()
    except FileNotFoundError:
        pass
    return filename
