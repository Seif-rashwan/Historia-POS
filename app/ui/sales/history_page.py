
import customtkinter as ctk
from tkinter import ttk, messagebox
from app.database import DB
from .invoice_viewer import InvoiceViewer

class HistoryPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.db = DB()  
        
        header = ctk.CTkFrame(self, height=50)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="INVOICE HISTORY", font=("Arial", 20, "bold")).pack(side="left", padx=20)
        ctk.CTkButton(header, text="Refresh", command=self.load, width=80, font=("Arial", 12)).pack(side="right", padx=10)
        
        filter_frm = ctk.CTkFrame(self)
        filter_frm.pack(fill="x", padx=10, pady=5)
        self.ent_search = ctk.CTkEntry(filter_frm, placeholder_text="Search Customer/ID...", font=("Arial", 12))
        self.ent_search.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(filter_frm, text="Search", command=self.load, width=100, font=("Arial", 12)).pack(side="left", padx=5)
        
        self.tree_inv = ttk.Treeview(self, columns=("ID", "Date", "Customer", "Items", "Total"), show="headings")
        self.tree_inv.pack(fill="both", expand=True, padx=10, pady=10)
        
        cols = {"ID": 60, "Date": 100, "Customer": 200, "Items": 80, "Total": 100}
        for c, w in cols.items():
            self.tree_inv.heading(c, text=c)
            self.tree_inv.column(c, width=w)
            
        self.tree_inv.bind("<Double-1>", self.open_invoice)
        
        footer = ctk.CTkFrame(self, height=50)
        footer.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(footer, text="VIEW DETAILS", command=self.open_invoice, fg_color="#3B8ED0", font=("Arial", 12)).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(footer, text="DELETE INVOICE & RESTORE STOCK", command=self.delete_inv, fg_color="#C0392B", font=("Arial", 12)).pack(side="right", padx=10, pady=10)
        
        self.load()

    def load(self):
        for i in self.tree_inv.get_children(): self.tree_inv.delete(i)
        search = self.ent_search.get().strip()
        sql = """SELECT i.id, i.date, c.name, COUNT(d.id), i.net_total FROM invoices i LEFT JOIN customers c ON i.customer_id=c.id LEFT JOIN invoice_details d ON i.id = d.invoice_id WHERE c.name LIKE ? OR i.id LIKE ? GROUP BY i.id ORDER BY i.id DESC"""
        param = f"%{search}%"
        for r in self.db.fetch_all(sql, (param, param)):
            self.tree_inv.insert("", "end", values=r)

    def open_invoice(self, event=None):
        sel = self.tree_inv.selection()
        if not sel: return
        InvoiceViewer(self, self.tree_inv.item(sel[0])['values'][0])

    def delete_inv(self):
        sel = self.tree_inv.selection()
        if not sel: return messagebox.showerror("Error", "Select invoice first")
        if not messagebox.askyesno("Confirm", "Delete Invoice? This will RESTORE items to their original store."): return
        
        iid = self.tree_inv.item(sel[0])['values'][0]
        store_res = self.db.fetch_one("SELECT store_id FROM invoices WHERE id=?", (iid,))
        sid = store_res[0] if store_res and store_res[0] else 1
        
        details = self.db.fetch_all("SELECT item_detail_id, qty, IFNULL(returned_qty, 0) FROM invoice_details WHERE invoice_id=?", (iid,))
        
        for did, qty, ret_qty in details:
            restore_qty = qty - ret_qty
            if restore_qty > 0:
                exists = self.db.fetch_one("SELECT quantity FROM store_stock WHERE item_detail_id=? AND store_id=?", (did, sid))
                if exists:
                    self.db.execute("UPDATE store_stock SET quantity = quantity + ? WHERE item_detail_id=? AND store_id=?", (restore_qty, did, sid))
                else:
                    self.db.execute("INSERT INTO store_stock (item_detail_id, store_id, quantity) VALUES (?,?,?)", (did, sid, restore_qty))

        # Delete related returns if any (optional but cleaner)
        # self.db.execute("DELETE FROM returns WHERE invoice_id=?", (iid,)) 
        # But we might keep them for logs? No, if invoice is gone, return links break.
        # But cascading delete usually handles this. Let's just do the main cleanup.

        self.db.execute("DELETE FROM invoices WHERE id=?", (iid,))
        self.db.execute("DELETE FROM invoice_details WHERE invoice_id=?", (iid,))
        messagebox.showinfo("Success", "Invoice Deleted & Stock Restored")
        self.load()
        if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
