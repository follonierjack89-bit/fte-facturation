import csv
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.database import storage
from app.logic.models import Client, Invoice, InvoiceLine, Item
from app.pdf.invoice_pdf import generate_invoice_pdf


class Sidebar(ttk.Frame):
    def __init__(self, master, on_select):
        super().__init__(master, padding=10)
        self.on_select = on_select
        self.buttons = {}
        for view in ["Clients", "Articles", "Factures", "Paramètres"]:
            btn = ttk.Button(self, text=view, command=lambda v=view: self.on_select(v))
            btn.pack(fill="x", pady=5)
            self.buttons[view] = btn


class ClientsFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.editing_client_id: int | None = None
        self.tree = ttk.Treeview(self, columns=("company", "city"), show="headings", height=8)
        self.tree.heading("company", text="Client")
        self.tree.heading("city", text="Ville")
        self.tree.pack(fill="x")
        self.tree.bind("<Double-1>", self.on_client_double_click)

        form = ttk.Frame(self)
        form.pack(fill="x", pady=10)
        self.company = tk.StringVar()
        self.street = tk.StringVar()
        self.zip_code = tk.StringVar()
        self.city = tk.StringVar()
        self.country = tk.StringVar(value="Switzerland")
        self.email = tk.StringVar()
        self.phone = tk.StringVar()
        self.internal_code = tk.StringVar()
        ttk.Label(form, text="Raison sociale").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.company, width=30).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Rue").grid(row=1, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.street, width=30).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="NPA").grid(row=2, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.zip_code, width=10).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="Ville").grid(row=3, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.city, width=30).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="Pays").grid(row=4, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.country, width=30).grid(row=4, column=1, sticky="w")
        ttk.Label(form, text="Email").grid(row=5, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.email, width=30).grid(row=5, column=1, sticky="w")
        ttk.Label(form, text="Téléphone").grid(row=6, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.phone, width=30).grid(row=6, column=1, sticky="w")
        ttk.Label(form, text="Code interne").grid(row=7, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.internal_code, width=30).grid(row=7, column=1, sticky="w")
        self.save_button = ttk.Button(form, text="Ajouter", command=self.save_client)
        self.save_button.grid(row=8, column=1, sticky="w", pady=5)
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for client in storage.list_clients():
            self.tree.insert("", "end", iid=str(client.id), values=(client.company, f"{client.zip_code} {client.city}"))

    def save_client(self):
        if not self.company.get():
            messagebox.showerror("Erreur", "Le nom du client est requis")
            return
        client = Client(
            id=self.editing_client_id,
            company=self.company.get(),
            street=self.street.get(),
            zip_code=self.zip_code.get(),
            city=self.city.get(),
            country=self.country.get(),
            email=self.email.get(),
            phone=self.phone.get(),
            internal_code=self.internal_code.get(),
        )
        storage.save_client(client)
        self.reset_form()
        self.refresh()

    def on_client_double_click(self, event):  # pylint: disable=unused-argument
        selection = self.tree.selection()
        if not selection:
            return
        try:
            client_id = int(selection[0])
        except ValueError:
            return
        try:
            client = storage.load_client(client_id)
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Erreur", str(exc))
            return
        self.fill_form_from_client(client)

    def fill_form_from_client(self, client: Client):
        self.editing_client_id = client.id
        self.company.set(client.company)
        self.street.set(client.street)
        self.zip_code.set(client.zip_code)
        self.city.set(client.city)
        self.country.set(client.country)
        self.email.set(client.email)
        self.phone.set(client.phone)
        self.internal_code.set(client.internal_code)
        self.save_button.config(text="Mettre à jour")

    def reset_form(self):
        self.editing_client_id = None
        self.company.set("")
        self.street.set("")
        self.zip_code.set("")
        self.city.set("")
        self.country.set("Switzerland")
        self.email.set("")
        self.phone.set("")
        self.internal_code.set("")
        self.save_button.config(text="Ajouter")


class ItemsFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.tree = ttk.Treeview(self, columns=("ref", "description", "price"), show="headings", height=8)
        for col, title in [("ref", "Article n°"), ("description", "Description"), ("price", "PU")]:
            self.tree.heading(col, text=title)
        self.tree.pack(fill="x")

        form = ttk.Frame(self)
        form.pack(fill="x", pady=10)
        self.reference = tk.StringVar()
        self.description = tk.StringVar()
        self.unit_price = tk.DoubleVar(value=0.0)
        ttk.Label(form, text="Article n°").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.reference, width=20).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Description").grid(row=1, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.description, width=30).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="PU").grid(row=2, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.unit_price, width=10).grid(row=2, column=1, sticky="w")
        ttk.Button(form, text="Ajouter", command=self.add_item).grid(row=3, column=1, sticky="w", pady=5)
        ttk.Button(form, text="Importer depuis Excel/CSV...", command=self.on_import_items).grid(
            row=3, column=2, sticky="w", padx=5
        )
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in storage.list_items():
            self.tree.insert("", "end", values=(item.reference, item.description, f"{item.unit_price:.2f}"))

    def on_import_items(self):
        filename = filedialog.askopenfilename(
            title="Importer des articles",
            filetypes=[
                ("Fichiers CSV/Excel", "*.csv *.xlsx *.xls"),
                ("CSV", "*.csv"),
                ("Tous les fichiers", "*.*"),
            ],
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != ".csv":
            messagebox.showinfo(
                "Format non pris en charge",
                "Merci d'enregistrer le fichier Excel au format CSV avant l'import.",
            )
            return
        try:
            inserted, updated, skipped = self.import_items_from_csv(path)
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Erreur d'import", str(exc))
            return
        self.refresh()
        messagebox.showinfo(
            "Import terminé",
            f"Articles ajoutés: {inserted}\nArticles mis à jour: {updated}\nLignes ignorées: {skipped}",
        )

    def import_items_from_csv(self, file_path: Path) -> tuple[int, int, int]:
        inserted = updated = skipped = 0
        with file_path.open(newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            headers = [h.strip() for h in reader.fieldnames or []]
            ref_key = self._find_column(headers, ["reference", "référence", "article", "article n°", "article no"])
            desc_key = self._find_column(headers, ["description", "desc"])
            price_key = self._find_column(headers, ["price", "unit_price", "prix", "pu", "prix unitaire"])
            if not ref_key or not desc_key or not price_key:
                raise ValueError("Colonnes requises manquantes (référence, description, prix)")
            for row in reader:
                try:
                    reference = (row.get(ref_key) or "").strip()
                    description = (row.get(desc_key) or "").strip()
                    price_raw = (row.get(price_key) or "").strip().replace(",", ".")
                    if not reference:
                        skipped += 1
                        continue
                    unit_price = float(price_raw)
                except Exception:  # pylint: disable=broad-except
                    skipped += 1
                    continue
                existing = storage.get_item_by_reference(reference)
                default_qty = existing.default_quantity if existing else 1.0
                item = Item(
                    id=existing.id if existing else None,
                    reference=reference,
                    description=description,
                    unit_price=unit_price,
                    default_quantity=default_qty,
                )
                storage.upsert_item(item)
                if existing:
                    updated += 1
                else:
                    inserted += 1
        return inserted, updated, skipped

    @staticmethod
    def _find_column(headers: list[str], candidates: list[str]) -> str | None:
        lower_headers = {h.lower(): h for h in headers}
        for candidate in candidates:
            if candidate.lower() in lower_headers:
                return lower_headers[candidate.lower()]
        return None

    def add_item(self):
        if not self.reference.get():
            messagebox.showerror("Erreur", "La référence est requise")
            return
        item = Item(
            id=None,
            reference=self.reference.get(),
            description=self.description.get(),
            unit_price=float(self.unit_price.get()),
        )
        storage.save_item(item)
        self.reference.set("")
        self.description.set("")
        self.unit_price.set(0.0)
        self.refresh()


class InvoiceFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.settings = storage.load_settings()
        self.client_var = tk.StringVar()
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.notes = tk.StringVar()
        self.lines: list[InvoiceLine] = []
        self.editing_line_index: int | None = None

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Client").grid(row=0, column=0, sticky="w")
        self.client_combo = ttk.Combobox(top, textvariable=self.client_var, width=40)
        self.client_combo.grid(row=0, column=1, sticky="w")
        ttk.Button(top, text="Recharger", command=self.load_clients).grid(row=0, column=2, padx=5)

        ttk.Label(top, text="Date").grid(row=1, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.date_var, width=20).grid(row=1, column=1, sticky="w")

        ttk.Label(top, text="Remarques").grid(row=2, column=0, sticky="nw")
        ttk.Entry(top, textvariable=self.notes, width=60).grid(row=2, column=1, sticky="w")

        self.lines_tree = ttk.Treeview(
            self,
            columns=("article", "description", "qty", "price", "discount", "total"),
            show="headings",
            height=6,
        )
        for col, title in [
            ("article", "Article"),
            ("description", "Description"),
            ("qty", "Qté"),
            ("price", "PU"),
            ("discount", "Remise %"),
            ("total", "Total"),
        ]:
            self.lines_tree.heading(col, text=title)
        self.lines_tree.bind("<Double-1>", self.on_line_double_click)
        self.lines_tree.pack(fill="x", pady=5)

        line_form = ttk.Frame(self)
        line_form.pack(fill="x", pady=5)
        self.line_article_number = tk.StringVar()
        self.line_description = tk.StringVar()
        self.line_qty = tk.DoubleVar(value=1.0)
        self.line_price = tk.DoubleVar(value=0.0)
        self.line_discount = tk.DoubleVar(value=0.0)
        ttk.Label(line_form, text="Article n°").grid(row=0, column=0)
        article_entry = ttk.Entry(line_form, textvariable=self.line_article_number, width=15)
        article_entry.grid(row=0, column=1)
        article_entry.bind("<Return>", self.on_article_number_enter)
        article_entry.bind("<FocusOut>", self.on_article_number_enter)
        ttk.Label(line_form, text="Description").grid(row=0, column=2)
        ttk.Entry(line_form, textvariable=self.line_description, width=30).grid(row=0, column=3)
        ttk.Label(line_form, text="Qté").grid(row=0, column=4)
        ttk.Entry(line_form, textvariable=self.line_qty, width=8).grid(row=0, column=5)
        ttk.Label(line_form, text="PU").grid(row=0, column=6)
        ttk.Entry(line_form, textvariable=self.line_price, width=10).grid(row=0, column=7)
        ttk.Label(line_form, text="Remise %").grid(row=0, column=8)
        ttk.Entry(line_form, textvariable=self.line_discount, width=8).grid(row=0, column=9)
        self.add_line_button = ttk.Button(line_form, text="Ajouter la ligne", command=self.add_line)
        self.add_line_button.grid(row=0, column=10, padx=5)

        action_bar = ttk.Frame(self)
        action_bar.pack(fill="x", pady=5)
        ttk.Button(action_bar, text="Enregistrer la facture", command=self.save_invoice).pack(side="left")
        ttk.Button(action_bar, text="Générer le PDF", command=self.generate_pdf).pack(side="left", padx=5)
        self.total_label = ttk.Label(action_bar, text="Total: 0.00 CHF")
        self.total_label.pack(side="right")

        self.load_clients()
        self.refresh_lines_tree()
        self.refresh_totals()

    def load_clients(self):
        clients = storage.list_clients()
        self.clients = {client.company: client for client in clients}
        self.client_combo["values"] = list(self.clients.keys())

    def on_article_number_enter(self, event=None):  # pylint: disable=unused-argument
        reference = self.line_article_number.get().strip()
        if not reference:
            return
        item = storage.get_item_by_reference(reference)
        if not item:
            return
        self.line_description.set(item.description)
        self.line_price.set(item.unit_price)

    def add_line(self):
        if not self.line_description.get():
            messagebox.showerror("Erreur", "Description requise")
            return
        try:
            quantity = float(self.line_qty.get())
            unit_price = float(self.line_price.get())
            discount = float(self.line_discount.get() or 0.0)
        except ValueError:
            messagebox.showerror("Erreur", "Valeurs numériques invalides")
            return
        if discount < 0 or discount > 100:
            messagebox.showerror("Erreur", "La remise doit être entre 0 et 100")
            return
        line = InvoiceLine(
            item=None,
            article_number=self.line_article_number.get(),
            description=self.line_description.get(),
            quantity=quantity,
            unit_price=unit_price,
            discount_percent=discount,
        )
        if self.editing_line_index is None:
            self.lines.append(line)
        else:
            self.lines[self.editing_line_index] = line
        self.reset_line_form()
        self.refresh_lines_tree()
        self.refresh_totals()

    def build_invoice(self) -> Invoice:
        client_name = self.client_var.get()
        if client_name not in self.clients:
            raise ValueError("Sélectionner un client existant")
        invoice_number = self.settings.generate_invoice_number()
        invoice_date = date.fromisoformat(self.date_var.get())
        return Invoice(
            id=None,
            number=invoice_number,
            invoice_date=invoice_date,
            client=self.clients[client_name],
            lines=self.lines,
            notes=self.notes.get(),
            vat_rate=self.settings.vat_rate if self.settings.vat_enabled else 0.0,
        )

    def on_line_double_click(self, event):  # pylint: disable=unused-argument
        selection = self.lines_tree.selection()
        if not selection:
            return
        index = self.lines_tree.index(selection[0])
        if index >= len(self.lines):
            return
        line = self.lines[index]
        self.editing_line_index = index
        self.line_article_number.set(line.article_number)
        self.line_description.set(line.description)
        self.line_qty.set(line.quantity)
        self.line_price.set(line.unit_price)
        self.line_discount.set(line.discount_percent)
        self.add_line_button.config(text="Mettre à jour la ligne")

    def refresh_lines_tree(self):
        for row in self.lines_tree.get_children():
            self.lines_tree.delete(row)
        for idx, line in enumerate(self.lines):
            self.lines_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    line.article_number,
                    line.description,
                    f"{line.quantity:.2f}",
                    f"{line.unit_price:.2f}",
                    f"{line.discount_percent:.2f}",
                    f"{line.total:.2f}",
                ),
            )

    def reset_line_form(self):
        self.editing_line_index = None
        self.line_article_number.set("")
        self.line_description.set("")
        self.line_qty.set(1.0)
        self.line_price.set(0.0)
        self.line_discount.set(0.0)
        self.add_line_button.config(text="Ajouter la ligne")

    def save_invoice(self):
        try:
            invoice = self.build_invoice()
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Erreur", str(exc))
            return
        storage.save_invoice(invoice)
        self.settings.next_number += 1
        storage.save_settings(self.settings)
        messagebox.showinfo("Succès", f"Facture {invoice.number} enregistrée")

    def generate_pdf(self):
        try:
            invoice = self.build_invoice()
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Erreur", str(exc))
            return
        filename = generate_invoice_pdf(invoice, self.settings, self.settings.logo_path or None)
        messagebox.showinfo("PDF créé", f"Enregistré sous {filename}")

    def refresh_totals(self):
        total = sum(line.total for line in self.lines)
        self.total_label.config(text=f"Total: {total:.2f} CHF")


class SettingsFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.settings = storage.load_settings()
        self.company = tk.StringVar(value=self.settings.company_name)
        self.street = tk.StringVar(value=self.settings.street)
        self.zip_code = tk.StringVar(value=self.settings.zip_code)
        self.city = tk.StringVar(value=self.settings.city)
        self.country = tk.StringVar(value=self.settings.country)
        self.qr_iban = tk.StringVar(value=self.settings.qr_iban)
        self.logo_path = tk.StringVar(value=self.settings.logo_path)
        self.prefix = tk.StringVar(value=self.settings.invoice_prefix)
        self.next_number = tk.IntVar(value=self.settings.next_number)
        self.vat_enabled = tk.BooleanVar(value=self.settings.vat_enabled)
        self.vat_rate = tk.DoubleVar(value=self.settings.vat_rate)

        form = ttk.Frame(self)
        form.pack(fill="x")
        fields = [
            ("Société", self.company),
            ("Rue", self.street),
            ("NPA", self.zip_code),
            ("Ville", self.city),
            ("Pays", self.country),
            ("QR-IBAN", self.qr_iban),
            ("Logo (chemin)", self.logo_path),
            ("Préfixe facture", self.prefix),
            ("Prochain numéro", self.next_number),
        ]
        for idx, (label, var) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=idx, column=0, sticky="w")
            ttk.Entry(form, textvariable=var, width=40).grid(row=idx, column=1, sticky="w")

        vat_row = len(fields)
        ttk.Checkbutton(form, text="TVA 7.7%", variable=self.vat_enabled).grid(row=vat_row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.vat_rate, width=10).grid(row=vat_row, column=1, sticky="w")

        ttk.Button(form, text="Enregistrer", command=self.save_settings).grid(row=vat_row + 1, column=1, sticky="w", pady=5)

    def save_settings(self):
        self.settings.company_name = self.company.get()
        self.settings.street = self.street.get()
        self.settings.zip_code = self.zip_code.get()
        self.settings.city = self.city.get()
        self.settings.country = self.country.get()
        self.settings.qr_iban = self.qr_iban.get()
        self.settings.logo_path = self.logo_path.get()
        self.settings.invoice_prefix = self.prefix.get()
        self.settings.next_number = int(self.next_number.get())
        self.settings.vat_enabled = bool(self.vat_enabled.get())
        self.settings.vat_rate = float(self.vat_rate.get())
        storage.save_settings(self.settings)
        messagebox.showinfo("Enregistré", "Paramètres sauvegardés")


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FTE Facturation")
        self.geometry("900x600")
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        sidebar = Sidebar(container, self.show_view)
        sidebar.pack(side="left", fill="y")
        self.main_area = ttk.Frame(container)
        self.main_area.pack(side="right", fill="both", expand=True)

        self.views = {
            "Clients": ClientsFrame(self.main_area),
            "Articles": ItemsFrame(self.main_area),
            "Factures": InvoiceFrame(self.main_area),
            "Paramètres": SettingsFrame(self.main_area),
        }
        for view in self.views.values():
            view.pack_forget()
        self.show_view("Factures")

    def show_view(self, name: str):
        for view_name, frame in self.views.items():
            if view_name == name:
                frame.pack(fill="both", expand=True)
                if hasattr(frame, "refresh"):
                    frame.refresh()
            else:
                frame.pack_forget()


def run_app():
    storage.init_db()
    app = MainWindow()
    app.mainloop()


__all__ = ["run_app"]
