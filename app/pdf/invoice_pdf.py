from datetime import datetime
from pathlib import Path
from typing import Optional

from fpdf import FPDF

from app.logic.models import Invoice, Settings

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


def _normalize_country(value: str) -> str:
    return "CH" if value.strip().lower() == "switzerland" else value


def create_swiss_qr_png(invoice: Invoice, settings: Settings, destination: Path, dpi: int = 300) -> Path:
    """Generate a fully compliant Swiss QR-bill PNG with the Swiss cross.

    To adapt the QR content:
    - Change the creditor IBAN/address by editing the `settings` values (e.g.,
      settings.qr_iban, settings.company_name, settings.street, settings.zip_code,
      settings.city, settings.country).
    - Debtor data is read from the `invoice.client` fields.
    - The amount is taken from `invoice.total`; adjust there to alter the QR amount.
    - Provide a reference (QRR or NON) by setting `invoice.reference` if/when
      the model is extended; currently we generate a NON-reference QR.
    """

    try:
        from swissqrbill import QRBill
        from swissqrbill.output import QRBillImage
    except Exception as exc:  # pragma: no cover - dependency/runtime check
        raise RuntimeError(
            "Le module 'swissqrbill' (et Pillow) est requis pour générer un QR-bill conforme."
        ) from exc

    creditor_country = _normalize_country(settings.country)
    debtor_country = _normalize_country(invoice.client.country)

    # Build the QR-bill data structure (white Swiss cross included by swissqrbill)
    bill = QRBill(
        account=settings.qr_iban.replace(" ", ""),
        creditor={
            "name": settings.company_name,
            "line1": settings.street,
            "line2": f"{settings.zip_code} {settings.city}",
            "country": creditor_country,
        },
        debtor={
            "name": invoice.client.company,
            "line1": invoice.client.street,
            "line2": f"{invoice.client.zip_code} {invoice.client.city}",
            "country": debtor_country,
        },
        amount=invoice.total,
        currency="CHF",
        reference=None,
        additional_information=invoice.notes or "",
    )

    qr_image = QRBillImage(bill, scale=10, dpi=dpi)
    qr_image.save(destination)
    return destination


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
    pdf.cell(25, 8, "Article", border=1)
    pdf.cell(55, 8, "Description", border=1)
    pdf.cell(20, 8, "Qté", border=1, align="R")
    pdf.cell(25, 8, "Prix", border=1, align="R")
    pdf.cell(25, 8, "Remise", border=1, align="R")
    pdf.cell(25, 8, "Total", border=1, align="R", ln=True)

    pdf.set_font("Helvetica", size=11)
    for line in invoice.lines:
        pdf.cell(25, 8, line.article_number or "", border=1)
        pdf.cell(55, 8, line.description, border=1)
        pdf.cell(20, 8, f"{line.quantity:.2f}", border=1, align="R")
        pdf.cell(25, 8, f"{line.unit_price:.2f}", border=1, align="R")
        pdf.cell(25, 8, f"{line.discount_percent:.2f}%", border=1, align="R")
        pdf.cell(25, 8, f"{line.total:.2f}", border=1, align="R", ln=True)

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

    qr_temp_path = Path(__file__).resolve().parent / "qr_temp.png"
    qr_image_path = create_swiss_qr_png(invoice, settings, qr_temp_path)

    qr_size_mm = 70
    x_pos = pdf.w - pdf.r_margin - qr_size_mm
    y_pos = pdf.h - pdf.b_margin - qr_size_mm - 15
    pdf.image(str(qr_image_path), x=x_pos, y=y_pos, w=qr_size_mm, h=qr_size_mm)

    pdf.set_xy(10, y_pos)
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


def generate_swiss_qr_invoice(invoice: Invoice, settings: Settings, logo_path: Optional[str] = None) -> Path:
    """Generate a PDF invoice embedding a compliant Swiss QR-bill image.

    This dedicated entry point ensures the QR is produced with the swissqrbill
    library (white Swiss cross included) before being embedded at the correct
    position in the PDF layout.
    """

    return generate_invoice_pdf(invoice, settings, logo_path)
