import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional

from app.logic.models import Client, Invoice, InvoiceLine, Item, Settings

DB_PATH = Path("fte_facturation.db")


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                street TEXT NOT NULL,
                zip_code TEXT NOT NULL,
                city TEXT NOT NULL,
                country TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                internal_code TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL,
                description TEXT NOT NULL,
                unit_price REAL NOT NULL,
                default_quantity REAL NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                client_id INTEGER NOT NULL,
                notes TEXT,
                vat_rate REAL NOT NULL,
                FOREIGN KEY(client_id) REFERENCES clients(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                item_id INTEGER,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id),
                FOREIGN KEY(item_id) REFERENCES items(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def save_client(client: Client) -> Client:
    with connection() as conn:
        cur = conn.cursor()
        if client.id:
            cur.execute(
                """
                UPDATE clients
                SET company=?, street=?, zip_code=?, city=?, country=?, email=?, phone=?, internal_code=?
                WHERE id=?
                """,
                (
                    client.company,
                    client.street,
                    client.zip_code,
                    client.city,
                    client.country,
                    client.email,
                    client.phone,
                    client.internal_code,
                    client.id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO clients(company, street, zip_code, city, country, email, phone, internal_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client.company,
                    client.street,
                    client.zip_code,
                    client.city,
                    client.country,
                    client.email,
                    client.phone,
                    client.internal_code,
                ),
            )
            client.id = cur.lastrowid
        conn.commit()
    return client


def list_clients() -> List[Client]:
    with connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, company, street, zip_code, city, country, email, phone, internal_code FROM clients ORDER BY company")
        rows = cur.fetchall()
    return [
        Client(
            id=row[0],
            company=row[1],
            street=row[2],
            zip_code=row[3],
            city=row[4],
            country=row[5],
            email=row[6] or "",
            phone=row[7] or "",
            internal_code=row[8] or "",
        )
        for row in rows
    ]


def save_item(item: Item) -> Item:
    with connection() as conn:
        cur = conn.cursor()
        if item.id:
            cur.execute(
                """
                UPDATE items
                SET reference=?, description=?, unit_price=?, default_quantity=?
                WHERE id=?
                """,
                (item.reference, item.description, item.unit_price, item.default_quantity, item.id),
            )
        else:
            cur.execute(
                """
                INSERT INTO items(reference, description, unit_price, default_quantity)
                VALUES (?, ?, ?, ?)
                """,
                (item.reference, item.description, item.unit_price, item.default_quantity),
            )
            item.id = cur.lastrowid
        conn.commit()
    return item


def list_items() -> List[Item]:
    with connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, reference, description, unit_price, default_quantity FROM items ORDER BY reference")
        rows = cur.fetchall()
    return [
        Item(id=row[0], reference=row[1], description=row[2], unit_price=row[3], default_quantity=row[4])
        for row in rows
    ]


def _load_client(conn: sqlite3.Connection, client_id: int) -> Client:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, company, street, zip_code, city, country, email, phone, internal_code FROM clients WHERE id=?",
        (client_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("Client not found")
    return Client(
        id=row[0],
        company=row[1],
        street=row[2],
        zip_code=row[3],
        city=row[4],
        country=row[5],
        email=row[6] or "",
        phone=row[7] or "",
        internal_code=row[8] or "",
    )


def load_client(client_id: int) -> Client:
    with connection() as conn:
        return _load_client(conn, client_id)


def save_invoice(invoice: Invoice) -> Invoice:
    with connection() as conn:
        cur = conn.cursor()
        if invoice.id:
            cur.execute(
                """
                UPDATE invoices SET number=?, invoice_date=?, client_id=?, notes=?, vat_rate=? WHERE id=?
                """,
                (
                    invoice.number,
                    invoice.invoice_date.isoformat(),
                    invoice.client.id,
                    invoice.notes,
                    invoice.vat_rate,
                    invoice.id,
                ),
            )
            cur.execute("DELETE FROM invoice_lines WHERE invoice_id=?", (invoice.id,))
        else:
            cur.execute(
                """
                INSERT INTO invoices(number, invoice_date, client_id, notes, vat_rate)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    invoice.number,
                    invoice.invoice_date.isoformat(),
                    invoice.client.id,
                    invoice.notes,
                    invoice.vat_rate,
                ),
            )
            invoice.id = cur.lastrowid

        for line in invoice.lines:
            cur.execute(
                """
                INSERT INTO invoice_lines(invoice_id, description, quantity, unit_price, item_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    invoice.id,
                    line.description,
                    line.quantity,
                    line.unit_price,
                    line.item.id if line.item else None,
                ),
            )
        conn.commit()
    return invoice


def list_invoices(conn: Optional[sqlite3.Connection] = None) -> List[Invoice]:
    own_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        own_conn = True
    cur = conn.cursor()
    cur.execute("SELECT id, number, invoice_date, client_id, notes, vat_rate FROM invoices ORDER BY id DESC")
    rows = cur.fetchall()
    invoices: List[Invoice] = []
    for row in rows:
        client = _load_client(conn, row[3])
        cur.execute(
            "SELECT description, quantity, unit_price, item_id FROM invoice_lines WHERE invoice_id=?",
            (row[0],),
        )
        line_rows = cur.fetchall()
        item_map = {item.id: item for item in list_items()}
        lines: List[InvoiceLine] = []
        for description, quantity, unit_price, item_id in line_rows:
            item = item_map.get(item_id) if item_id else None
            lines.append(
                InvoiceLine(item=item, description=description, quantity=quantity, unit_price=unit_price)
            )
        invoices.append(
            Invoice(
                id=row[0],
                number=row[1],
                invoice_date=date.fromisoformat(row[2]),
                client=client,
                lines=lines,
                notes=row[4] or "",
                vat_rate=row[5],
            )
        )
    if own_conn:
        conn.close()
    return invoices


def load_settings() -> Settings:
    with connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT data FROM settings WHERE id=1")
        row = cur.fetchone()
        if not row:
            default_settings = Settings()
            save_settings(default_settings)
            return default_settings
        data = json.loads(row[0])
    return Settings(**data)


def save_settings(settings: Settings) -> None:
    with connection() as conn:
        cur = conn.cursor()
        data = json.dumps(asdict(settings))
        cur.execute("INSERT OR REPLACE INTO settings(id, data) VALUES (1, ?)", (data,))
        conn.commit()


__all__ = [
    "init_db",
    "save_client",
    "load_client",
    "list_clients",
    "save_item",
    "list_items",
    "save_invoice",
    "list_invoices",
    "load_settings",
    "save_settings",
]
