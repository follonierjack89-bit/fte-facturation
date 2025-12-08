import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

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
        self.tree = ttk.Treeview(self, columns=("company", "city"), show="headings", height=8)
        self.tree.heading("company", text="Client")
        self.tree.heading("city", text="Ville")
        self.tree.pack(fill="x")

        form = ttk.Frame(self)
        form.pack(fill="x", pady=10)
        self.company = tk.StringVar()
        self.street = tk.StringVar()
        self.zip_code = tk.StringVar()
        self.city = tk.StringVar()
        self.country = tk.StringVar(value="Switzerland")
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
        ttk.Button(form, text="Ajouter", command=self.add_client).grid(row=5, column=1, sticky="w", pady=5)
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for client in storage.list_clients():
            self.tree.insert("", "end", values=(client.company, f"{client.zip_code} {client.city}"))

    def add_client(self):
        if not self.company.get():
            messagebox.showerror("Erreur", "Le nom du client est requis")
            return
        client = Client(
            id=None,
            company=self.company.get(),
            street=self.street.get(),
            zip_code=self.zip_code.get(),
            city=self.city.get(),
            country=self.country.get(),
        )
        storage.save_client(client)
        self.company.set("")
        self.street.set("")
        self.zip_code.set("")
        self.city.set("")
        self.refresh()


class ItemsFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.tree = ttk.Treeview(self, columns=("ref", "description", "price"), show="headings", height=8)
        for col, title in [("ref", "Référence"), ("description", "Description"), ("price", "Prix")]:
            self.tree.heading(col, text=title)
        self.tree.pack(fill="x")

        form = ttk.Frame(self)
        form.pack(fill="x", pady=10)
        self.reference = tk.StringVar()
        self.description = tk.StringVar()
        self.unit_price = tk.DoubleVar(value=0.0)
        ttk.Label(form, text="Référence").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.reference, width=20).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Description").grid(row=1, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.description, width=30).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="Prix unitaire").grid(row=2, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.unit_price, width=10).grid(row=2, column=1, sticky="w")
        ttk.Button(form, text="Ajouter", command=self.add_item).grid(row=3, column=1, sticky="w", pady=5)
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in storage.list_items():
            self.tree.insert("", "end", values=(item.reference, item.description, f"{item.unit_price:.2f}"))

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

        self.lines_tree = ttk.Treeview(self, columns=("description", "qty", "price", "total"), show="headings", height=6)
        for col, title in [("description", "Description"), ("qty", "Qté"), ("price", "PU"), ("total", "Total")]:
            self.lines_tree.heading(col, text=title)
        self.lines_tree.pack(fill="x", pady=5)

        line_form = ttk.Frame(self)
        line_form.pack(fill="x", pady=5)
        self.line_description = tk.StringVar()
        self.line_qty = tk.DoubleVar(value=1.0)
        self.line_price = tk.DoubleVar(value=0.0)
        ttk.Label(line_form, text="Description").grid(row=0, column=0)
        ttk.Entry(line_form, textvariable=self.line_description, width=30).grid(row=0, column=1)
        ttk.Label(line_form, text="Qté").grid(row=0, column=2)
        ttk.Entry(line_form, textvariable=self.line_qty, width=8).grid(row=0, column=3)
        ttk.Label(line_form, text="PU").grid(row=0, column=4)
        ttk.Entry(line_form, textvariable=self.line_price, width=10).grid(row=0, column=5)
        ttk.Button(line_form, text="Ajouter la ligne", command=self.add_line).grid(row=0, column=6, padx=5)

        action_bar = ttk.Frame(self)
        action_bar.pack(fill="x", pady=5)
        ttk.Button(action_bar, text="Enregistrer la facture", command=self.save_invoice).pack(side="left")
        ttk.Button(action_bar, text="Générer le PDF", command=self.generate_pdf).pack(side="left", padx=5)
        self.total_label = ttk.Label(action_bar, text="Total: 0.00 CHF")
        self.total_label.pack(side="right")

        self.load_clients()
        self.refresh_totals()

    def load_clients(self):
        clients = storage.list_clients()
        self.clients = {client.company: client for client in clients}
        self.client_combo["values"] = list(self.clients.keys())

    def add_line(self):
        if not self.line_description.get():
            messagebox.showerror("Erreur", "Description requise")
            return
        line = InvoiceLine(
            item=None,
            description=self.line_description.get(),
            quantity=float(self.line_qty.get()),
            unit_price=float(self.line_price.get()),
        )
        self.lines.append(line)
        self.lines_tree.insert("", "end", values=(line.description, line.quantity, line.unit_price, line.total))
        self.line_description.set("")
        self.line_qty.set(1.0)
        self.line_price.set(0.0)
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
