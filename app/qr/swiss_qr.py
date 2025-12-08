from app.logic.models import Invoice, Settings


def build_payload(invoice: Invoice, settings: Settings) -> str:
    """Build the Swiss QR bill payload following SPC 0200 field order."""

    def normalize_country(value: str) -> str:
        return "CH" if value.strip().lower() == "switzerland" else value

    creditor_country = normalize_country(settings.country)
    debtor_country = normalize_country(invoice.client.country)

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
