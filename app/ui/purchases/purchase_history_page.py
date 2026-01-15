import customtkinter as ctk
from tkinter import ttk, messagebox
from app.database import DB

class PurchaseHistoryPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.db = DB()  
        
        header = ctk.CTkFrame(self, height=50)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="PURCHASE INVOICE HISTORY", font=("Arial", 20, "bold")).pack(side="left", padx=20)
        ctk.CTkButton(header, text="Refresh", command=self.load, width=80, font=("Arial", 12)).pack(side="right", padx=10)
        
        filter_frm = ctk.CTkFrame(self)
        filter_frm.pack(fill="x", padx=10, pady=5)
        self.ent_search = ctk.CTkEntry(filter_frm, placeholder_text="Search Supplier/ID...", font=("Arial", 12))
        self.ent_search.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(filter_frm, text="Search", command=self.load, width=100, font=("Arial", 12)).pack(side="left", padx=5)
        
        self.tree = ttk.Treeview(self, columns=("ID", "Date", "Supplier", "Items", "Total", "Store"), show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        cols = {"ID": 60, "Date": 100, "Supplier": 200, "Items": 80, "Total": 100, "Store": 120}
        for c, w in cols.items():
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)
            
        footer = ctk.CTkFrame(self, height=50)
        footer.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(footer, text="DELETE PURCHASE & REVERSE STOCK", command=self.delete_inv, fg_color="#C0392B", font=("Arial", 12)).pack(side="right", padx=10, pady=10)
        
        self.load()

    def load(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        search = self.ent_search.get().strip()
        sql = """
            SELECT p.id, p.date, s.name, COUNT(d.id), p.net_total, st.name
            FROM purchases p 
            LEFT JOIN suppliers s ON p.supplier_id=s.id 
            LEFT JOIN purchase_details d ON p.id = d.purchase_id 
            LEFT JOIN stores st ON p.store_id = st.id
            WHERE s.name LIKE ? OR p.id LIKE ? 
            GROUP BY p.id 
            ORDER BY p.id DESC
        """
        param = f"%{search}%"
        for r in self.db.fetch_all(sql, (param, param)):
            self.tree.insert("", "end", values=r)

    def delete_inv(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showerror("Error", "Select invoice first")
        
        try:
            iid = self.tree.item(sel[0])['values'][0]
            
            # ========================================
            # CHECK FOR MANUFACTURING LINKAGE
            # ========================================
            # Check if this is a Material invoice (has child Factory invoice)
            child_invoice = self.db.fetch_one("SELECT id FROM purchases WHERE parent_purchase_id=?", (iid,))
            
            # Check if this is a Factory invoice (has parent Material invoice)
            parent_invoice = self.db.fetch_one("SELECT parent_purchase_id FROM purchases WHERE id=?", (iid,))
            parent_id = parent_invoice[0] if parent_invoice and parent_invoice[0] else None
            
            if child_invoice:
                # This is a Material invoice with linked Factory invoice
                if not messagebox.askyesno("Manufacturing Order", 
                    f"This is a Manufacturing Material Invoice linked to Factory Invoice #{child_invoice[0]}.\n\n" +
                    "Deleting this will also delete the linked Factory invoice.\n\nContinue?"):
                    return
            elif parent_id:
                # This is a Factory invoice linked to Material invoice
                if not messagebox.askyesno("Manufacturing Order",
                    f"This is a Manufacturing Factory Invoice linked to Material Invoice #{parent_id}.\n\n" +
                    "Deleting this will also delete the linked Material invoice AND reverse stock.\n\nContinue?"):
                    return
            
            if not messagebox.askyesno("Confirm", "Delete Purchase? This will REMOVE items from the stock."): return
            
            # ========================================
            # DELETION LOGIC
            # ========================================
            store_res = self.db.fetch_one("SELECT store_id FROM purchases WHERE id=?", (iid,))
            sid = store_res[0] if store_res else 1
            
            # Reduce Stock (Reverse the Purchase) - Only for Material invoices or standalone
            if not parent_id:  # If this is NOT a factory invoice
                for did, qty in self.db.fetch_all("SELECT item_detail_id, qty FROM purchase_details WHERE purchase_id=?", (iid,)):
                    current_qty = self.db.fetch_one("SELECT quantity FROM store_stock WHERE item_detail_id=? AND store_id=?", (did, sid))
                    if current_qty and current_qty[0] < qty:
                        if not messagebox.askyesno("Warning", f"Insufficient stock to reverse item {did}. Continue anyway? (Stock will become negative)"):
                            return
                    
                    self.db.execute("UPDATE store_stock SET quantity = quantity - ? WHERE item_detail_id=? AND store_id=?", (qty, did, sid))
            
            # Delete linked invoices
            if child_invoice:
                # Delete child Factory invoice first
                self.db.execute("DELETE FROM purchases WHERE id=?", (child_invoice[0],))
                self.db.execute("DELETE FROM purchase_details WHERE purchase_id=?", (child_invoice[0],))
            
            if parent_id:
                # Delete parent Material invoice AND its stock
                for did, qty in self.db.fetch_all("SELECT item_detail_id, qty FROM purchase_details WHERE purchase_id=?", (parent_id,)):
                    self.db.execute("UPDATE store_stock SET quantity = quantity - ? WHERE item_detail_id=? AND store_id=?", (qty, did, sid))
                
                self.db.execute("DELETE FROM purchases WHERE id=?", (parent_id,))
                self.db.execute("DELETE FROM purchase_details WHERE purchase_id=?", (parent_id,))
            
            # Delete main invoice
            self.db.execute("DELETE FROM purchases WHERE id=?", (iid,))
            self.db.execute("DELETE FROM purchase_details WHERE purchase_id=?", (iid,))
            
            messagebox.showinfo("Success", "Purchase Deleted and Stock Reversed")
            self.load()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")
