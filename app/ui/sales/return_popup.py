
import customtkinter as ctk
from tkinter import messagebox
from app.database import DB
from datetime import date

class ReturnPopup(ctk.CTkToplevel):
    def __init__(self, parent, invoice_id):
        super().__init__(parent)
        self.title(f"Process Return - Invoice #{invoice_id}")
        self.geometry("900x650")
        self.db = DB()
        self.invoice_id = invoice_id
        self.grab_set()
        
        inv = self.db.fetch_one("SELECT date, payment_method, store_id, net_total FROM invoices WHERE id=?", (invoice_id,))
        self.orig_date, self.orig_method, self.store_id, self.orig_total = inv
        
        info_frm = ctk.CTkFrame(self, fg_color="gray20")
        info_frm.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(info_frm, text=f"Original Date: {self.orig_date}", font=("Arial", 12)).pack(side="left", padx=15, pady=10)
        ctk.CTkLabel(info_frm, text=f"Original Payment: {self.orig_method}", font=("Arial", 12, "bold"), text_color="#3B8ED0").pack(side="left", padx=15)
        ctk.CTkLabel(info_frm, text=f"Total Value: {self.orig_total}", font=("Arial", 12)).pack(side="left", padx=15)
        
        ctk.CTkLabel(self, text="Select Items & Qty to Return:", font=("Arial", 14, "bold")).pack(anchor="w", padx=15)
        self.scroll = ctk.CTkScrollableFrame(self, height=250)
        self.scroll.pack(fill="x", padx=10, pady=5)
        
        h_frm = ctk.CTkFrame(self.scroll, fg_color="gray30", height=30)
        h_frm.pack(fill="x")
        for txt, w in [("Item Name", 250), ("Price", 80), ("Sold", 60), ("Prev. Ret", 60), ("RETURN QTY", 100)]:
            ctk.CTkLabel(h_frm, text=txt, width=w, font=("Arial", 11, "bold")).pack(side="left", padx=2)
            
        self.return_entries = []
        self.load_items()
        
        act_frm = ctk.CTkFrame(self, fg_color="gray25")
        act_frm.pack(fill="both", expand=True, padx=10, pady=10)
        
        opts = ctk.CTkFrame(act_frm, fg_color="transparent")
        opts.pack(side="left", fill="y", padx=20, pady=20)
        
        ctk.CTkLabel(opts, text="Refund From Safe:", font=("Arial", 12)).grid(row=0, column=2, pady=5, sticky="w", padx=(10,0))
        self.cb_safe = ctk.CTkComboBox(opts, values=[], font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_safe.grid(row=0, column=3, pady=5, padx=5)
        
        self.load_safes()

        ctk.CTkLabel(opts, text="Refund Method:", font=("Arial", 12)).grid(row=1, column=0, pady=5, sticky="w")
        self.cb_refund_method = ctk.CTkComboBox(opts, values=["Cash", "Visa", "Store Credit/Exchange"], font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_refund_method.grid(row=1, column=1, pady=5)
        self.cb_refund_method.set(self.orig_method)
        
        ctk.CTkLabel(opts, text="Deduction (Fees/Damage):", font=("Arial", 12)).grid(row=2, column=0, pady=5, sticky="w")
        self.ent_deduction = ctk.CTkEntry(opts, placeholder_text="0.00", font=("Arial", 12))
        self.ent_deduction.grid(row=2, column=1, pady=5)
        self.ent_deduction.bind("<KeyRelease>", self.calc_total)
        
        ctk.CTkLabel(opts, text="Notes:", font=("Arial", 12)).grid(row=3, column=0, pady=5, sticky="nw")
        self.txt_notes = ctk.CTkTextbox(opts, width=200, height=60, font=("Arial", 12))
        self.txt_notes.grid(row=3, column=1, pady=5)
        
        tots = ctk.CTkFrame(act_frm, fg_color="transparent")
        tots.pack(side="right", fill="y", padx=30, pady=20)
        
        self.lbl_subtotal = ctk.CTkLabel(tots, text="Item Value: 0.00", font=("Arial", 14))
        self.lbl_subtotal.pack(anchor="e", pady=2)
        
        self.lbl_net = ctk.CTkLabel(tots, text="NET REFUND: 0.00", font=("Arial", 20, "bold"), text_color="#E74C3C")
        self.lbl_net.pack(anchor="e", pady=10)
        
        ctk.CTkButton(tots, text="CONFIRM RETURN", command=self.save_return, fg_color="#C0392B", height=40, font=("Arial", 12, "bold")).pack(pady=10)

    def load_safes(self):
        safes = self.db.fetch_all("SELECT name FROM safes")
        vals = [s[0] for s in safes]
        self.cb_safe.configure(values=vals)
        if vals: self.cb_safe.set(vals[0])

    def load_items(self):
        items = self.db.fetch_all("""SELECT id.id, i.name, id.price, id.qty, IFNULL(id.returned_qty, 0), id.item_note FROM invoice_details id JOIN item_details d ON id.item_detail_id = d.id JOIN items i ON d.item_id = i.id WHERE id.invoice_id = ?""", (self.invoice_id,))
        for it in items:
            detail_id, name, price, sold, ret, note = it
            if note: name += f" {note}"
            max_ret = sold - ret
            if max_ret > 0:
                row = ctk.CTkFrame(self.scroll, height=35)
                row.pack(fill="x", pady=1)
                ctk.CTkLabel(row, text=name, width=250, anchor="w", font=("Arial", 12)).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=f"{price}", width=80, font=("Arial", 12)).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=f"{sold}", width=60, font=("Arial", 12)).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=f"{ret}", width=60, text_color="orange", font=("Arial", 12)).pack(side="left", padx=2)
                ent = ctk.CTkEntry(row, width=100, font=("Arial", 12))
                ent.pack(side="left", padx=5)
                ent.insert(0, "0")
                ent.bind("<KeyRelease>", self.calc_total)
                self.return_entries.append({"id": detail_id, "price": price, "max": max_ret, "entry": ent})

    def calc_total(self, event=None):
        total = 0.0
        for item in self.return_entries:
            try:
                qty = float(item["entry"].get())
                if qty > item["max"]: 
                    item["entry"].configure(text_color="red")
                else: 
                    item["entry"].configure(text_color="white")
                    total += qty * item["price"]
            except: pass
        self.lbl_subtotal.configure(text=f"Item Value: {total:,.2f}")
        try: ded = float(self.ent_deduction.get())
        except: ded = 0.0
        net = total - ded
        self.lbl_net.configure(text=f"NET REFUND: {net:,.2f}")
        return net

    def save_return(self):
        refund_val = self.calc_total()
        if refund_val <= 0 and not messagebox.askyesno("Confirm", "Net Refund is 0 or negative. Continue?"): return
        
        items_to_return = []
        for item in self.return_entries:
            try:
                qty = float(item["entry"].get())
                if qty > 0:
                    if qty > item["max"]: return messagebox.showerror("Error", f"Qty exceeds limit for an item.")
                    items_to_return.append((item["id"], qty))
            except: pass
        
        if not items_to_return: return messagebox.showerror("Error", "No items selected.")
        
        # Safe Check
        safe_name = self.cb_safe.get()
        safe_res = self.db.fetch_one("SELECT id FROM safes WHERE name=?", (safe_name,))
        if not safe_res: return messagebox.showerror("Error", "Invalid Safe Selected")
        safe_id = safe_res[0]

        try:
            for detail_id, qty in items_to_return:
                self.db.execute("UPDATE invoice_details SET returned_qty = IFNULL(returned_qty, 0) + ? WHERE id=?", (qty, detail_id))
                res = self.db.fetch_one("SELECT item_detail_id FROM invoice_details WHERE id=?", (detail_id,))
                self.db.execute("UPDATE store_stock SET quantity = quantity + ? WHERE item_detail_id=? AND store_id=?", (qty, res[0], self.store_id))
            
            notes = f"Method: {self.cb_refund_method.get()} | {self.txt_notes.get('1.0', 'end').strip()}"
            self.db.execute("INSERT INTO returns (date, invoice_id, qty, refund_amount, notes) VALUES (?,?,?,?,?)", (date.today(), self.invoice_id, len(items_to_return), refund_val, notes))
            
            # --- CREATE VOUCHER FOR REFUND (Money Out) ---
            if refund_val > 0:
                self.db.execute("INSERT INTO vouchers (date, voucher_type, safe_id, amount, description) VALUES (?,?,?,?,?)", 
                               (date.today(), 'Payment', safe_id, refund_val, f"Refund for Invoice #{self.invoice_id}"))

            messagebox.showinfo("Success", "Return Processed Successfully (Stock Updated + Voucher Created)")
            self.destroy()
            if hasattr(self.master, 'load_invoices'): self.master.load_invoices()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")
