from dataclasses import dataclass
from typing import Optional

from app.logic.models import Client, Invoice, Settings


@dataclass
class SwissQRPayload:
    account: str
    creditor_name: str
    creditor_street: str
    creditor_zip: str
    creditor_city: str
    creditor_country: str
    amount: Optional[float]
    currency: str
    debtor_name: str
    debtor_street: str
    debtor_zip: str
    debtor_city: str
    debtor_country: str

    def to_text(self) -> str:
        amount_value = f"{self.amount:.2f}" if self.amount is not None else ""
        fields = [
            "SPC",
            "0200",
            "1",
            self.account,
            "K",
            self.creditor_name,
            self.creditor_street,
            f"{self.creditor_zip} {self.creditor_city}",
            self.creditor_country,
            "",
            "",
            "",
            "",
            amount_value,
            self.currency,
            self.debtor_name,
            self.debtor_street,
            f"{self.debtor_zip} {self.debtor_city}",
            self.debtor_country,
            "",
            "",
            "",
            "EPD",
        ]
        return "\n".join(fields)


def build_payload(invoice: Invoice, settings: Settings) -> SwissQRPayload:
    def normalize_country(value: str) -> str:
        return "CH" if value.strip().lower() == "switzerland" else value

    return SwissQRPayload(
        account=settings.qr_iban,
        creditor_name=settings.company_name,
        creditor_street=settings.street,
        creditor_zip=settings.zip_code,
        creditor_city=settings.city,
        creditor_country=normalize_country(settings.country),
        amount=invoice.total,
        currency="CHF",
        debtor_name=invoice.client.company,
        debtor_street=invoice.client.street,
        debtor_zip=invoice.client.zip_code,
        debtor_city=invoice.client.city,
        debtor_country=normalize_country(invoice.client.country),
    )
