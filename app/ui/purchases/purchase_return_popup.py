
import customtkinter as ctk
from tkinter import messagebox
from app.database import DB
from datetime import date

class PurchaseReturnPopup(ctk.CTkToplevel):
    def __init__(self, parent, purchase_id, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.title(f"Purchase Return - Invoice #{purchase_id}")
        self.geometry("900x650")
        self.db = DB()
        self.purchase_id = purchase_id
        self.grab_set()
        
        # Load Purchase Info
        pur = self.db.fetch_one("SELECT date, payment_method, store_id, net_total FROM purchases WHERE id=?", (purchase_id,))
        if not pur:
             self.destroy()
             return
        self.orig_date, self.orig_method, self.store_id, self.orig_total = pur
        
        info_frm = ctk.CTkFrame(self, fg_color="gray20")
        info_frm.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(info_frm, text=f"Date: {self.orig_date}", font=("Arial", 12)).pack(side="left", padx=15, pady=10)
        ctk.CTkLabel(info_frm, text=f"Method: {self.orig_method}", font=("Arial", 12, "bold"), text_color="#3B8ED0").pack(side="left", padx=15)
        ctk.CTkLabel(info_frm, text=f"Total: {self.orig_total}", font=("Arial", 12)).pack(side="left", padx=15)
        
        ctk.CTkLabel(self, text="Select Items to Return to Supplier:", font=("Arial", 14, "bold")).pack(anchor="w", padx=15)
        self.scroll = ctk.CTkScrollableFrame(self, height=250)
        self.scroll.pack(fill="x", padx=10, pady=5)
        
        h_frm = ctk.CTkFrame(self.scroll, fg_color="gray30", height=30)
        h_frm.pack(fill="x")
        for txt, w in [("Item Name", 250), ("Buy Price", 80), ("Bot Qty", 60), ("Prev Ret", 60), ("RETURN QTY", 100)]:
            ctk.CTkLabel(h_frm, text=txt, width=w, font=("Arial", 11, "bold")).pack(side="left", padx=2)
            
        self.return_entries = []
        self.load_items()
        
        act_frm = ctk.CTkFrame(self, fg_color="gray25")
        act_frm.pack(fill="both", expand=True, padx=10, pady=10)
        
        opts = ctk.CTkFrame(act_frm, fg_color="transparent")
        opts.pack(side="left", fill="y", padx=20, pady=20)
        
        ctk.CTkLabel(opts, text="Notes:", font=("Arial", 12)).grid(row=0, column=0, pady=5, sticky="nw")
        self.txt_notes = ctk.CTkTextbox(opts, width=200, height=60, font=("Arial", 12))
        self.txt_notes.grid(row=0, column=1, pady=5)
        
        tots = ctk.CTkFrame(act_frm, fg_color="transparent")
        tots.pack(side="right", fill="y", padx=30, pady=20)
        
        self.lbl_subtotal = ctk.CTkLabel(tots, text="Return Value: 0.00", font=("Arial", 14))
        self.lbl_subtotal.pack(anchor="e", pady=2)
        
        ctk.CTkButton(tots, text="CONFIRM RETURN", command=self.save_return, fg_color="#C0392B", height=40, font=("Arial", 12, "bold")).pack(pady=10)

    def load_items(self):
        # Join with item_details and items
        sql = """SELECT pd.id, i.name, pd.buy_price, pd.qty, IFNULL(pd.returned_qty, 0) 
                 FROM purchase_details pd 
                 JOIN item_details d ON pd.item_detail_id = d.id 
                 JOIN items i ON d.item_id = i.id 
                 WHERE pd.purchase_id = ?"""
        items = self.db.fetch_all(sql, (self.purchase_id,))
        
        for it in items:
            detail_id, name, price, bought, ret = it
            max_ret = bought - ret
            if max_ret > 0:
                row = ctk.CTkFrame(self.scroll, height=35)
                row.pack(fill="x", pady=1)
                ctk.CTkLabel(row, text=name, width=250, anchor="w", font=("Arial", 12)).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=f"{price}", width=80, font=("Arial", 12)).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=f"{bought}", width=60, font=("Arial", 12)).pack(side="left", padx=2)
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
        self.lbl_subtotal.configure(text=f"Return Value: {total:,.2f}")
        return total

    def save_return(self):
        refund_val = self.calc_total()
        if refund_val <= 0: return messagebox.showerror("Error", "Total is 0 or invalid.")
        
        items_to_return = []
        for item in self.return_entries:
            try:
                qty = float(item["entry"].get())
                if qty > 0:
                    if qty > item["max"]: return messagebox.showerror("Error", f"Qty exceeds limit for an item.")
                    items_to_return.append((item["id"], qty))
            except: pass
        
        if not items_to_return: return messagebox.showerror("Error", "No items selected.")
        
        try:
            for pd_id, qty in items_to_return:
                # Update purchase_details
                self.db.execute("UPDATE purchase_details SET returned_qty = IFNULL(returned_qty, 0) + ? WHERE id=?", (qty, pd_id))
                
                # Update Stock (Remove from store because we are returning to supplier)
                res = self.db.fetch_one("SELECT item_detail_id FROM purchase_details WHERE id=?", (pd_id,))
                item_detail_id = res[0]
                
                # Check if stock exists
                stock = self.db.fetch_one("SELECT quantity FROM store_stock WHERE item_detail_id=? AND store_id=?", (item_detail_id, self.store_id))
                current_qty = stock[0] if stock else 0
                
                if current_qty < qty:
                     raise ValueError(f"Not enough stock in store to return item (ID: {item_detail_id})")

                self.db.execute("UPDATE store_stock SET quantity = quantity - ? WHERE item_detail_id=? AND store_id=?", (qty, item_detail_id, self.store_id))
            
            notes = self.txt_notes.get('1.0', 'end').strip()
            # self.db.execute("INSERT INTO purchase_returns (date, invoice_id, qty, refund_amount, notes) VALUES (?,?,?,?,?)", ...)
            # Wait, table is purchase_returns. Columns?
            # From Delete Logic: "DELETE FROM purchase_returns WHERE id=?"
            # Schema not fully visible but likely similar to returns.
            # Assuming columns: date, purchase_id, qty, refund_amount, notes
            # 'invoice_id' in returns table corresponds to 'purchase_id' here? Or 'purchase_id' column?
            # Let's assume 'purchase_id' column for transparency, or 'invoice_id' if reused (but likely separate table).
            # From `main.py` lines 4104: `SELECT ... FROM returns r` (Sales Returns).
            # I haven't seen `purchase_returns` schema creation.
            # But line 2927 deletes from `purchase_returns`.
            # I will assume `purchase_id` column.
            
            # Insert Master Return Record
            # qty here is just count of items or total pieces? Usually row count or total pieces. 
            # Original code logged len(items). Let's stick effectively to that or total qty.
            ret_id = self.db.execute("INSERT INTO purchase_returns (date, purchase_id, qty, refund_amount, notes) VALUES (?,?,?,?,?)", 
                           (date.today(), self.purchase_id, sum(q for _, q in items_to_return), refund_val, notes))
            
            # Insert Return Details
            for pd_id, qty in items_to_return:
                self.db.execute("INSERT INTO purchase_return_details (purchase_return_id, purchase_detail_id, qty) VALUES (?,?,?)", (ret_id, pd_id, qty))
            
            messagebox.showinfo("Success", "Purchase Return Processed Successfully!")
            self.destroy()

            
            if hasattr(self.master, 'load_history'):
                self.master.load_history()
            
            if self.controller and hasattr(self.controller, 'refresh_views'):
                self.controller.refresh_views()

        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")
