
import customtkinter as ctk
from tkinter import ttk
from app.database import DB

class InvoiceViewer(ctk.CTkToplevel):
    def __init__(self, parent, invoice_id):
        super().__init__(parent)
        self.title(f"Invoice Details #{invoice_id}")
        self.geometry("1000x700")
        self.db = DB()
        self.invoice_id = invoice_id
        self.grab_set()
        
        sql = """SELECT i.date, c.name, c.phone, c.address, s.name, i.channel, i.payment_method, sf.name, i.delegate_name, i.net_total, i.tax_percent, i.discount_percent, i.shipping_cost, i.notes FROM invoices i LEFT JOIN customers c ON i.customer_id = c.id LEFT JOIN stores s ON i.store_id = s.id LEFT JOIN safes sf ON i.safe_id = sf.id WHERE i.id = ?"""
        inv_data = self.db.fetch_one(sql, (invoice_id,))
        if not inv_data:
            self.destroy()
            return
            
        (i_date, c_name, c_phone, c_addr, s_name, channel, pay_method, safe_name, delegate, net_total, tax_pct, disc_val, ship_cost, notes) = inv_data
        
        header = ctk.CTkFrame(self, fg_color="gray20", corner_radius=10)
        header.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(header, text=f"INVOICE #{invoice_id}", font=("Arial", 16, "bold"), text_color="#3B8ED0").grid(row=0, column=0, padx=15, pady=10)
        ctk.CTkLabel(header, text=f"Date: {i_date}", font=("Arial", 12)).grid(row=0, column=1, padx=15)
        ctk.CTkLabel(header, text=f"Store: {s_name}", font=("Arial", 12)).grid(row=0, column=2, padx=15)
        
        ctk.CTkLabel(header, text="Customer:", text_color="gray", font=("Arial", 12)).grid(row=1, column=0, sticky="e", padx=5)
        lbl_cust = ctk.CTkEntry(header, width=150, font=("Arial", 12))
        lbl_cust.insert(0, c_name or "Unknown")
        lbl_cust.grid(row=1, column=1, padx=5, pady=5)
        lbl_cust.configure(state="readonly")
        
        ctk.CTkLabel(header, text="Phone:", font=("Arial", 12)).grid(row=1, column=2, sticky="e", padx=5)
        lbl_phone = ctk.CTkEntry(header, width=120, font=("Arial", 12))
        lbl_phone.insert(0, c_phone or "")
        lbl_phone.grid(row=1, column=3, padx=5)
        lbl_phone.configure(state="readonly")
        
        ctk.CTkLabel(header, text="Channel:", font=("Arial", 12)).grid(row=1, column=4, sticky="e", padx=5)
        lbl_chan = ctk.CTkEntry(header, width=120, font=("Arial", 12))
        lbl_chan.insert(0, channel or "-")
        lbl_chan.grid(row=1, column=5, padx=5)
        lbl_chan.configure(state="readonly")
        
        logistics = ctk.CTkFrame(self, fg_color="gray25")
        logistics.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(logistics, text=f"Payment: {pay_method}", font=("Arial", 12)).pack(side="left", padx=15, pady=5)
        if safe_name:
            ctk.CTkLabel(logistics, text=f"Safe: {safe_name}", font=("Arial", 12)).pack(side="left", padx=15)
        ctk.CTkLabel(logistics, text=f"Delivery: {delegate}", font=("Arial", 12)).pack(side="left", padx=15)
        
        cols = ("Barcode", "Item Name", "Color", "Size", "Qty", "Price", "Total")
        tree = ttk.Treeview(self, columns=cols, show="headings", height=10)
        tree.pack(fill="both", expand=True, padx=15, pady=10)
        
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=80)
        tree.column("Item Name", width=200)
        
        items = self.db.fetch_all("""SELECT d.barcode, i.name, c.name, s.name, id.qty, id.price, id.total, id.item_note FROM invoice_details id JOIN item_details d ON id.item_detail_id = d.id JOIN items i ON d.item_id = i.id LEFT JOIN colors c ON d.color_id = c.id LEFT JOIN sizes s ON d.size_id = s.id WHERE id.invoice_id = ?""", (invoice_id,))
        subtotal = 0
        for item in items:
            # item: 0=barcode, 1=name, 2=cname, 3=sname, 4=qty, 5=price, 6=total, 7=item_note
            vals = list(item[:7]) # Copy first 7 elements
            if item[7]: # item_note
                vals[1] += f" {item[7]}" # Append to Name
            
            tree.insert("", "end", values=vals)
            subtotal += item[6]
            
        footer = ctk.CTkFrame(self, fg_color="gray20", height=150)
        footer.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(footer, text="Notes:", font=("Arial", 12)).pack(side="left", anchor="nw", padx=10, pady=10)
        txt_notes = ctk.CTkTextbox(footer, width=300, height=80, font=("Arial", 12))
        txt_notes.pack(side="left", padx=5, pady=10)
        txt_notes.insert("1.0", notes or "No notes")
        txt_notes.configure(state="disabled")
        
        totals_frame = ctk.CTkFrame(footer, fg_color="transparent")
        totals_frame.pack(side="right", padx=20, pady=10)
        
        def add_row(txt, val, r):
            ctk.CTkLabel(totals_frame, text=txt, font=("Arial", 12)).grid(row=r, column=0, sticky="e", padx=5)
            lbl = ctk.CTkLabel(totals_frame, text=str(val), font=("Arial", 12, "bold"))
            lbl.grid(row=r, column=1, sticky="w", padx=5)
            
        add_row("Subtotal:", f"{subtotal:,.2f}", 0)
        add_row("Discount:", f"-{disc_val:,.2f}", 1)
        
        after_disc = subtotal - disc_val
        tax_val = after_disc * (tax_pct / 100)
        add_row(f"Tax ({tax_pct}%):", f"+{tax_val:,.2f}", 2)
        add_row("Shipping:", f"+{ship_cost:,.2f}", 3)
        
        ctk.CTkLabel(totals_frame, text="NET TOTAL:", font=("Arial", 14, "bold"), text_color="#2CC985").grid(row=4, column=0, pady=10)
        ctk.CTkLabel(totals_frame, text=f"{net_total:,.2f}", font=("Arial", 18, "bold"), text_color="#2CC985").grid(row=4, column=1, pady=10)
        
        btn_frm = ctk.CTkFrame(footer, fg_color="transparent")
        btn_frm.pack(side="right", anchor="s", padx=20, pady=20)
        ctk.CTkButton(btn_frm, text="EDIT INVOICE", width=120, fg_color="#3B8ED0", command=self.request_edit, font=("Arial", 12)).pack(side="left", padx=5)

    def request_edit(self):
        self.destroy()
        # Call edit_old_invoice on the controller (InventoryApp)
        # Note: self.master is usually the parent frame (HistoryPage), so we need self.master.controller
        if hasattr(self.master, 'controller'):
             self.master.controller.edit_old_invoice(self.invoice_id)
        elif hasattr(self.master, 'master') and hasattr(self.master.master, 'edit_old_invoice'):
             self.master.master.edit_old_invoice(self.invoice_id)
        else:
             print("Error: Could not find controller to edit invoice")
