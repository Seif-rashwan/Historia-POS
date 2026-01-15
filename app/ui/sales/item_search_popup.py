
import customtkinter as ctk
from app.database import DB

class ItemSearchPopup(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("بحث متطور عن صنف")
        self.geometry("500x400")
        self.callback = callback
        self.db = DB()
        self.grab_set()
        
        ctk.CTkLabel(self, text="اختر مواصفات المنتج:", font=("Arial", 16, "bold")).pack(pady=10)
        
        # 1. Product Name
        ctk.CTkLabel(self, text="اسم الصنف:", font=("Arial", 12)).pack(pady=(10,0))
        self.cb_name = ctk.CTkComboBox(self, width=300, command=self.on_name_change, font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_name.pack(pady=5)
        
        # 2. Color
        ctk.CTkLabel(self, text="اللون:", font=("Arial", 12)).pack(pady=(10,0))
        self.cb_color = ctk.CTkComboBox(self, width=300, command=self.on_color_change, font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_color.pack(pady=5)
        
        # 3. Size
        ctk.CTkLabel(self, text="المقاس:", font=("Arial", 12)).pack(pady=(10,0))
        self.cb_size = ctk.CTkComboBox(self, width=300, command=self.update_info, font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_size.pack(pady=5)
        
        # Info Label (Stock & Price)
        self.lbl_info = ctk.CTkLabel(self, text="", font=("Arial", 14, "bold"), text_color="#F39C12")
        self.lbl_info.pack(pady=20)
        
        # Add Button
        self.btn_add = ctk.CTkButton(self, text="إضافة للفاتورة", command=self.add_item, state="disabled", fg_color="#27AE60", font=("Arial", 12, "bold"))
        self.btn_add.pack(pady=10)
        
        self.current_barcode = None
        self.load_names()

    def load_names(self):
        # Ignore items starting with HD
        sql = """
            SELECT DISTINCT i.name 
            FROM items i
            JOIN item_details d ON i.id = d.item_id
            WHERE d.barcode NOT LIKE 'HD%'
            ORDER BY i.name
        """
        names = self.db.fetch_all(sql)
        vals = [n[0] for n in names]
        self.cb_name.configure(values=vals)
        if vals: 
            self.cb_name.set(vals[0])
            self.on_name_change(vals[0])

    def on_name_change(self, choice):
        sql = """
            SELECT DISTINCT IFNULL(c.name, 'No Color') 
            FROM item_details d 
            JOIN items i ON d.item_id=i.id 
            LEFT JOIN colors c ON d.color_id=c.id 
            WHERE i.name=? AND d.barcode NOT LIKE 'HD%'
        """
        colors = self.db.fetch_all(sql, (choice,))
        vals = [c[0] for c in colors]
        self.cb_color.configure(values=vals)
        if vals:
            self.cb_color.set(vals[0])
            self.on_color_change(vals[0])
            
    def on_color_change(self, choice):
        item_name = self.cb_name.get()
        color_val = None if choice == 'No Color' else choice
        
        sql = """
            SELECT DISTINCT IFNULL(s.name, 'No Size')
            FROM item_details d 
            JOIN items i ON d.item_id=i.id 
            LEFT JOIN colors c ON d.color_id=c.id 
            LEFT JOIN sizes s ON d.size_id=s.id 
            WHERE i.name=? AND (c.name=? OR (? IS NULL AND c.name IS NULL))
            AND d.barcode NOT LIKE 'HD%'
        """
        sizes = self.db.fetch_all(sql, (item_name, color_val, color_val))
        vals = [s[0] for s in sizes]
        self.cb_size.configure(values=vals)
        if vals:
            self.cb_size.set(vals[0])
            self.update_info(vals[0])

    def update_info(self, choice):
        item = self.cb_name.get()
        col = self.cb_color.get()
        siz = self.cb_size.get()
        
        c_val = None if col == 'No Color' else col
        s_val = None if siz == 'No Size' else siz
        
        sql = """
            SELECT d.barcode, d.sell_price 
            FROM item_details d
            JOIN items i ON d.item_id=i.id
            LEFT JOIN colors c ON d.color_id=c.id
            LEFT JOIN sizes s ON d.size_id=s.id
            WHERE i.name=? 
            AND (c.name=? OR (? IS NULL AND c.name IS NULL))
            AND (s.name=? OR (? IS NULL AND s.name IS NULL))
        """
        res = self.db.fetch_one(sql, (item, c_val, c_val, s_val, s_val))
        if res:
            self.current_barcode = res[0]
            price = res[1]
            self.lbl_info.configure(text=f"الباركود: {res[0]}\nالسعر: {price}")
            self.btn_add.configure(state="normal")
        else:
            self.lbl_info.configure(text="غير موجود")
            self.btn_add.configure(state="disabled")

    def add_item(self):
        if self.current_barcode:
            self.callback(self.current_barcode)
            self.destroy()
