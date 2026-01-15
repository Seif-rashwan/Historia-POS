import customtkinter as ctk
from tkinter import ttk, messagebox
from app.database import DB
from datetime import date

class ReturnsPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)  # <--- FIXED: These lines are now indented correctly
        self.controller = controller
        self.db = DB()
        
        # Header
        header = ctk.CTkFrame(self, height=50)
        header.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(header, text="SALES RETURNS MANAGER", font=("Arial", 20, "bold"), text_color="#E74C3C").pack(side="left", padx=20)
        
        # Search Box
        search_box = ctk.CTkFrame(self)
        search_box.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(search_box, text="Search Invoice:", font=("Arial", 12)).pack(side="left", padx=10)
        
        self.ent_search = ctk.CTkEntry(search_box, placeholder_text="Invoice ID / Customer Name", width=250, font=("Arial", 12))
        self.ent_search.pack(side="left", padx=5)
        self.ent_search.bind("<KeyRelease>", self.load_invoices)
        
        ctk.CTkButton(search_box, text="OPEN RETURN WINDOW", command=self.open_return_window, fg_color="#E67E22", font=("Arial", 12, "bold")).pack(side="right", padx=10)
        
        # Treeview
        self.tree = ttk.Treeview(self, columns=("ID", "Date", "Customer", "Total", "Payment", "Items"), show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        for c, w in [("ID", 60), ("Date", 100), ("Customer", 200), ("Total", 100), ("Payment", 100), ("Items", 80)]:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center")
            
        self.tree.bind("<Double-1>", self.open_return_window)
        self.load_invoices()

    def load_invoices(self, event=None):
        for i in self.tree.get_children():
            self.tree.delete(i)
        query = self.ent_search.get().strip()
        sql = """SELECT i.id, i.date, c.name, i.net_total, i.payment_method, COUNT(d.id) 
                 FROM invoices i 
                 LEFT JOIN customers c ON i.customer_id = c.id 
                 LEFT JOIN invoice_details d ON i.id = d.invoice_id 
                 WHERE CAST(i.id AS TEXT) LIKE ? OR c.name LIKE ? 
                 GROUP BY i.id ORDER BY i.id DESC"""
        param = f"%{query}%"
        rows = self.db.fetch_all(sql, (param, param))
        for r in rows:
            self.tree.insert("", "end", values=r)

    def open_return_window(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showerror("Error", "Please select an invoice first.")
        
        invoice_id = self.tree.item(sel[0])['values'][0]
        invoice_id = self.tree.item(sel[0])['values'][0]
        ReturnPopup(self, invoice_id)

# --- Popup Class Included Here to Avoid Import Errors ---
class ReturnPopup(ctk.CTkToplevel):
    def __init__(self, parent, invoice_id):
        super().__init__(parent)
        self.title(f"Process Return - Invoice #{invoice_id}")
        self.geometry("1000x650")
        self.db = DB()
        self.invoice_id = invoice_id
        self.grab_set()
        
        # Load Invoice Data
        inv = self.db.fetch_one("SELECT date, payment_method, store_id, net_total, customer_id, safe_id FROM invoices WHERE id=?", (invoice_id,))
        if not inv:
            self.destroy()
            return
            
        self.orig_date, self.orig_method, self.store_id, self.orig_total, self.customer_id, self.orig_safe_id = inv
        
        # Info Header
        info_frm = ctk.CTkFrame(self, fg_color="gray20")
        info_frm.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(info_frm, text=f"Date: {self.orig_date}", font=("Arial", 12)).pack(side="left", padx=15, pady=10)
        ctk.CTkLabel(info_frm, text=f"Payment: {self.orig_method}", font=("Arial", 12, "bold"), text_color="#3B8ED0").pack(side="left", padx=15)
        ctk.CTkLabel(info_frm, text=f"Total: {self.orig_total}", font=("Arial", 12)).pack(side="left", padx=15)
        
        ctk.CTkLabel(self, text="Select Items & Qty to Return:", font=("Arial", 14, "bold")).pack(anchor="w", padx=15)
        
        # Scrollable Item List
        self.scroll = ctk.CTkScrollableFrame(self, height=250)
        self.scroll.pack(fill="x", padx=10, pady=5)
        
        # Header Row
        h_frm = ctk.CTkFrame(self.scroll, fg_color="gray30", height=30)
        h_frm.pack(fill="x")
        labels = [("Item Name", 150), ("Color", 70), ("Size", 60), ("Design", 120), ("Price", 70), ("Sold", 50), ("Prev Ret", 70), ("Return Qty", 90)]
        for txt, w in labels:
            ctk.CTkLabel(h_frm, text=txt, width=w, font=("Arial", 11, "bold")).pack(side="left", padx=2)
            
        self.return_entries = []
        self.load_items()
        
        # Action Area
        act_frm = ctk.CTkFrame(self, fg_color="gray25")
        act_frm.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left Side: Options
        opts = ctk.CTkFrame(act_frm, fg_color="transparent")
        opts.pack(side="left", fill="y", padx=20, pady=20)
        
        ctk.CTkLabel(opts, text="Refund Method:", font=("Arial", 12)).grid(row=0, column=0, pady=5, sticky="w")
        self.cb_refund_method = ctk.CTkComboBox(opts, values=["Cash", "Visa", "Store Credit"], font=("Arial", 12))
        self.cb_refund_method.grid(row=0, column=1, pady=5)
        self.cb_refund_method.set(self.orig_method)

        ctk.CTkLabel(opts, text="Refund From Safe:", font=("Arial", 12)).grid(row=0, column=2, pady=5, sticky="w", padx=10)
        self.cb_safe = ctk.CTkComboBox(opts, width=150, font=("Arial", 12))
        self.cb_safe.grid(row=0, column=3, pady=5)
        self.load_safes()
        
        ctk.CTkLabel(opts, text="Deduction (Fees):", font=("Arial", 12)).grid(row=1, column=0, pady=5, sticky="w")
        self.ent_deduction = ctk.CTkEntry(opts, placeholder_text="0.00", font=("Arial", 12))
        self.ent_deduction.grid(row=1, column=1, pady=5)
        self.ent_deduction.bind("<KeyRelease>", self.calc_total)
        
        ctk.CTkLabel(opts, text="Notes:", font=("Arial", 12)).grid(row=2, column=0, pady=5, sticky="nw")
        self.txt_notes = ctk.CTkTextbox(opts, width=200, height=60, font=("Arial", 12))
        self.txt_notes.grid(row=2, column=1, pady=5)
        
        # Right Side: Totals
        tots = ctk.CTkFrame(act_frm, fg_color="transparent")
        tots.pack(side="right", fill="y", padx=30, pady=20)
        
        self.lbl_subtotal = ctk.CTkLabel(tots, text="Item Value: 0.00", font=("Arial", 14))
        self.lbl_subtotal.pack(anchor="e", pady=2)
        
        self.lbl_net = ctk.CTkLabel(tots, text="NET REFUND: 0.00", font=("Arial", 20, "bold"), text_color="#E74C3C")
        self.lbl_net.pack(anchor="e", pady=10)
        
        ctk.CTkButton(tots, text="CONFIRM RETURN", command=self.save_return, fg_color="#C0392B", height=40, font=("Arial", 12, "bold")).pack(pady=10)

    def load_safes(self):
        safes = self.db.fetch_all("SELECT id, name FROM safes")
        self.safe_map = {name: id for id, name in safes}
        self.cb_safe.configure(values=list(self.safe_map.keys()))
        
        # Try to set default safe matching the invoice safe
        default_safe_name = ""
        for name, id in self.safe_map.items():
            if id == self.orig_safe_id:
                default_safe_name = name
                break
        if default_safe_name:
            self.cb_safe.set(default_safe_name)
        elif safes:
            self.cb_safe.set(safes[0][1])

    def load_items(self):
        # Fetch ALL details: item name, color, size, design (item_note), price, qty, returned_qty
        items = self.db.fetch_all("""
            SELECT 
                id.id, 
                i.name, 
                c.name as color_name, 
                s.name as size_name,
                id.item_note,
                id.price, 
                id.qty, 
                IFNULL(id.returned_qty, 0) 
            FROM invoice_details id 
            JOIN item_details d ON id.item_detail_id = d.id 
            JOIN items i ON d.item_id = i.id 
            LEFT JOIN colors c ON d.color_id = c.id
            LEFT JOIN sizes s ON d.size_id = s.id
            WHERE id.invoice_id = ?
            ORDER BY id.id
        """, (self.invoice_id,))
                                     
        for it in items:
            detail_id, name, color, size, item_note, price, sold, ret = it
            max_ret = sold - ret
            
            if max_ret > 0:
                row = ctk.CTkFrame(self.scroll, height=35)
                row.pack(fill="x", pady=1)
                
                # Extract design name from item_note if it exists
                design_name = "Plain"
                if item_note and item_note.strip():
                    # item_note format is " [Design Name]"
                    design_name = item_note.strip()
                    if design_name.startswith("[") and design_name.endswith("]"):
                        design_name = design_name[1:-1]  # Remove brackets
                
                # Display all details
                ctk.CTkLabel(row, text=name, width=150, anchor="w", font=("Arial", 12)).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=color or "-", width=70, anchor="center", font=("Arial", 12)).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=size or "-", width=60, anchor="center", font=("Arial", 12)).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=design_name, width=120, anchor="w", font=("Arial", 12)).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=f"{price}", width=70, font=("Arial", 12)).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=f"{sold}", width=50, font=("Arial", 12)).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=f"{ret}", width=70, text_color="orange", font=("Arial", 12)).pack(side="left", padx=2)
                
                ent = ctk.CTkEntry(row, width=90, font=("Arial", 12))
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
            except:
                pass
        
        self.lbl_subtotal.configure(text=f"Item Value: {total:,.2f}")
        
        try:
            ded = float(self.ent_deduction.get())
        except:
            ded = 0.0
            
        net = total - ded
        self.lbl_net.configure(text=f"NET REFUND: {net:,.2f}")
        return net

    def save_return(self):
        refund_val = self.calc_total()
        if refund_val <= 0 and not messagebox.askyesno("Confirm", "Net Refund is 0 or less. Continue?"):
            return
            
        items_to_return = []
        for item in self.return_entries:
            try:
                qty = float(item["entry"].get())
                if qty > 0:
                    if qty > item["max"]:
                        return messagebox.showerror("Error", "Qty exceeds allowed limit")
                    items_to_return.append((item["id"], qty))
            except:
                pass
                
        if not items_to_return:
            return messagebox.showerror("Error", "No items selected")
            
        try:
            for detail_id, qty in items_to_return:
                # Update Invoice Detail
                self.db.execute("UPDATE invoice_details SET returned_qty = IFNULL(returned_qty, 0) + ? WHERE id=?", (qty, detail_id))
                
                # Get Item ID to return to stock
                res = self.db.fetch_one("SELECT item_detail_id FROM invoice_details WHERE id=?", (detail_id,))
                
                # Return stock to original store
                self.db.execute("UPDATE store_stock SET quantity = quantity + ? WHERE item_detail_id=? AND store_id=?", (qty, res[0], self.store_id))
            
            notes = f"Method: {self.cb_refund_method.get()} | {self.txt_notes.get('1.0', 'end').strip()}"
            self.db.execute("INSERT INTO returns (date, invoice_id, qty, refund_amount, notes) VALUES (?,?,?,?,?)", 
                           (date.today(), self.invoice_id, len(items_to_return), refund_val, notes))
            
            # FINANCIAL TRANSACTION (Deduct from Safe)
            method = self.cb_refund_method.get()
            if method != "Store Credit" and refund_val > 0:
                safe_name = self.cb_safe.get()
                if safe_name in self.safe_map:
                    safe_id = self.safe_map[safe_name]
                    desc = f"Return/Refund for Invoice #{self.invoice_id}"
                    self.db.execute("INSERT INTO vouchers (date, voucher_type, safe_id, amount, description, customer_id) VALUES (?,?,?,?,?,?)",
                                   (date.today(), "Payment", safe_id, refund_val, desc, self.customer_id))
                           
            messagebox.showinfo("Success", "Return Processed Successfully!")
            self.destroy()
            self.master.load_invoices()
            if hasattr(self.master, 'controller') and hasattr(self.master.controller, 'refresh_views'):
                self.master.controller.refresh_views()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")