
import customtkinter as ctk
from tkinter import ttk
from app.database import DB

class StoreDetailsPopup(ctk.CTkToplevel):
    def __init__(self, parent, store_id, store_name):
        super().__init__(parent)
        self.title(f"Stock Details: {store_name}")
        self.geometry("900x600")
        self.db = DB()
        self.grab_set() 
        header = ctk.CTkFrame(self, height=50, fg_color="gray20")
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text=f"ITEMS IN: {store_name}", font=("Arial", 20, "bold"), text_color="#3B8ED0").pack(pady=10)
        cols = ("Barcode", "Item Name", "Color", "Size", "Quantity", "Sell Price")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        for c, w in zip(cols, [150, 250, 80, 80, 80, 100]):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center" if c in ["Quantity", "Sell Price"] else "w")
        sql = """SELECT d.barcode, i.name, IFNULL(c.name,'-'), IFNULL(s.name,'-'), ss.quantity, d.sell_price FROM store_stock ss JOIN item_details d ON ss.item_detail_id = d.id JOIN items i ON d.item_id = i.id LEFT JOIN colors c ON d.color_id = c.id LEFT JOIN sizes s ON d.size_id = s.id WHERE ss.store_id = ? AND ss.quantity != 0 ORDER BY i.name"""
        items = self.db.fetch_all(sql, (store_id,))
        total_qty = 0
        total_val = 0
        for item in items:
            self.tree.insert("", "end", values=item)
            total_qty += item[4]
            total_val += (item[4] * item[5])
        footer = ctk.CTkFrame(self, height=40, fg_color="gray25")
        footer.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(footer, text=f"Total Items: {int(total_qty)}", font=("Arial", 14, "bold")).pack(side="left", padx=20)
        ctk.CTkLabel(footer, text=f"Total Stock Value: {total_val:,.2f} LE", font=("Arial", 14, "bold"), text_color="#2CC985").pack(side="right", padx=20)
