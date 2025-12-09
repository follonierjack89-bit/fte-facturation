from pathlib import Path
from typing import Optional

from app.logic.models import Invoice, Settings


def _normalize_country(value: str) -> str:
    return "CH" if value.strip().lower() == "switzerland" else value


def build_payload(invoice: Invoice, settings: Settings) -> str:
    """Legacy SPC 0200 payload builder (kept for backward compatibility)."""

    creditor_country = _normalize_country(settings.country)
    debtor_country = _normalize_country(invoice.client.country)

    amount_value = f"{invoice.total:.2f}" if invoice.total is not None else ""

    lines = [
        "SPC",  # Header: QR type
        "0200",  # Version
        "1",  # Coding type
        settings.qr_iban,  # Account
        "K",  # Creditor address type (structured)
        settings.company_name,
        settings.street,
        "",  # Creditor house number (not stored separately)
        settings.zip_code,
        settings.city,
        creditor_country,
        "",  # Ultimate creditor (5 empty lines)
        "",
        "",
        "",
        "",
        "CHF",  # Currency
        amount_value,  # Amount
        "K",  # Debtor address type (structured)
        invoice.client.company,
        invoice.client.street,
        "",  # Debtor house number (not stored separately)
        invoice.client.zip_code,
        invoice.client.city,
        debtor_country,
        "NON",  # Reference type (non-structured)
        "",  # Reference number
        "",  # Additional information
        "EPD",  # Trailer
        "",  # Alternative scheme 1
        "",  # Alternative scheme 2
    ]

    return "\n".join(lines)


def generate_qr_png(invoice: Invoice, settings: Settings, destination: Path, reference: Optional[str] = None, dpi: int = 300) -> Path:
    """Generate a fully compliant Swiss QR code with the Swiss cross using qrbill.

    This helper relies on the maintained qrbill package to ensure ISO 20022
    compliance and embeds the white Swiss cross in the center of the QR symbol.
    """

    try:
        from qrbill import QRBill
    except Exception as exc:  # pragma: no cover - runtime environment concern
        raise RuntimeError(
            "Le module 'qrbill' est requis pour générer un QR-bill conforme."
        ) from exc

    try:
        from cairosvg import svg2png
    except Exception as exc:  # pragma: no cover - runtime environment concern
        raise RuntimeError(
            "Le module 'cairosvg' est requis pour convertir le QR-bill SVG en PNG."
        ) from exc

    creditor_country = _normalize_country(settings.country)
    debtor_country = _normalize_country(invoice.client.country)

    reference_value = None if reference in (None, "NON", "") else reference

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
        reference=reference_value,
        additional_information=invoice.notes or "",
    )

    svg_path = destination.with_suffix(".svg")
    bill.as_svg(str(svg_path))
    svg2png(url=str(svg_path), write_to=str(destination), dpi=dpi)
    try:
        svg_path.unlink()
    except FileNotFoundError:
        pass
    return destination
