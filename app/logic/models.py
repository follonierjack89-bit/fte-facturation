from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class Client:
    id: Optional[int]
    company: str
    street: str
    zip_code: str
    city: str
    country: str = "Switzerland"
    email: str = ""
    phone: str = ""
    internal_code: str = ""


@dataclass
class Item:
    id: Optional[int]
    reference: str
    description: str
    unit_price: float
    default_quantity: float = 1.0


@dataclass
class InvoiceLine:
    item: Optional[Item]
    article_number: str
    description: str
    quantity: float
    unit_price: float
    discount_percent: float = 0.0

    @property
    def total(self) -> float:
        discount_factor = 1 - (self.discount_percent or 0.0) / 100.0
        return round(self.quantity * self.unit_price * discount_factor, 2)


@dataclass
class Invoice:
    id: Optional[int]
    number: str
    invoice_date: date
    client: Client
    lines: List[InvoiceLine] = field(default_factory=list)
    notes: str = ""
    vat_rate: float = 0.077

    @property
    def subtotal(self) -> float:
        return round(sum(line.total for line in self.lines), 2)

    @property
    def vat_amount(self) -> float:
        return round(self.subtotal * self.vat_rate, 2) if self.vat_rate else 0.0

    @property
    def total(self) -> float:
        return round(self.subtotal + self.vat_amount, 2)


@dataclass
class Settings:
    company_name: str = "FTE Sàrl"
    street: str = "Rue Centrale 104"
    zip_code: str = "1983"
    city: str = "Evolène"
    country: str = "Switzerland"
    qr_iban: str = "CH0000000000000000000"
    vat_enabled: bool = True
    vat_rate: float = 0.077
    logo_path: str = ""
    invoice_prefix: str = "2025-"
    next_number: int = 1

    def generate_invoice_number(self) -> str:
        return f"{self.invoice_prefix}{self.next_number:03d}"
