
import customtkinter as ctk
from tkinter import messagebox
from app.database import DB

class TransferPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.db = DB()
        self.detail_id = None
        # Header
        header = ctk.CTkFrame(self, height=60, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 20))
        ctk.CTkLabel(header, text="STOCK TRANSFER", font=("Arial", 24, "bold"), text_color="#E67E22").pack(side="left", padx=20)
        
        # Main Container
        container = ctk.CTkFrame(self, fg_color="gray20", corner_radius=15)
        container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 1. Store Selection
        store_frm = ctk.CTkFrame(container, fg_color="gray25", corner_radius=10)
        store_frm.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(store_frm, text="Source Store:", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=15, pady=15, sticky="e")
        self.cb_from = ctk.CTkComboBox(store_frm, width=220, font=("Arial", 14), height=35)
        self.cb_from.grid(row=0, column=1, padx=10, pady=15)
        
        # Arrow Icon (or just label)
        ctk.CTkLabel(store_frm, text="➔", font=("Arial", 24, "bold"), text_color="#F39C12").grid(row=0, column=2, padx=20)
        
        ctk.CTkLabel(store_frm, text="Destination Store:", font=("Arial", 14, "bold")).grid(row=0, column=3, padx=15, pady=15, sticky="e")
        self.cb_to = ctk.CTkComboBox(store_frm, width=220, font=("Arial", 14), height=35)
        self.cb_to.grid(row=0, column=4, padx=10, pady=15)
        
        # 2. Item Scan
        scan_frm = ctk.CTkFrame(container, fg_color="transparent")
        scan_frm.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(scan_frm, text="Item Barcode:", font=("Arial", 14)).pack(side="left", padx=(10, 5))
        self.ent_code = ctk.CTkEntry(scan_frm, width=300, height=40, placeholder_text="Scan Item Barcode...", font=("Arial", 14))
        self.ent_code.pack(side="left", padx=5)
        self.ent_code.bind("<Return>", self.lookup)
        
        ctk.CTkButton(scan_frm, text="Check Stock", command=lambda: self.lookup(None), width=120, height=40, 
                      fg_color="#2980B9", font=("Arial", 12, "bold")).pack(side="left", padx=15)
        
        # Info Display Card
        self.info_card = ctk.CTkFrame(container, fg_color="gray30", corner_radius=10, border_color="#34495E", border_width=2)
        self.info_card.pack(fill="x", padx=40, pady=20)
        self.lbl_info = ctk.CTkLabel(self.info_card, text="Ready to scan...", font=("Arial", 16), text_color="gray80")
        self.lbl_info.pack(pady=15)
        
        # 3. Quantity & Action
        action_frm = ctk.CTkFrame(container, fg_color="transparent")
        action_frm.pack(pady=20)
        
        ctk.CTkLabel(action_frm, text="Transfer Quantity:", font=("Arial", 16, "bold")).pack(side="left", padx=10)
        self.ent_qty = ctk.CTkEntry(action_frm, width=100, height=40, font=("Arial", 16), justify="center")
        self.ent_qty.pack(side="left", padx=10)
        
        ctk.CTkButton(container, text="CONFIRM TRANSFER", command=self.do_transfer, fg_color="#D35400", hover_color="#BA4A00",
                      height=50, width=300, font=("Arial", 16, "bold")).pack(pady=30)
        self.load_stores()

    def load_stores(self):
        s = [x[0] for x in self.db.fetch_all("SELECT name FROM stores")]
        if s: 
            self.cb_from.configure(values=s)
            self.cb_from.set(s[0])
            self.cb_to.configure(values=s)
            self.cb_to.set(s[1] if len(s)>1 else s[0])

    def lookup(self, e):
        code = self.ent_code.get().strip()
        store = self.cb_from.get()
        sql = """SELECT d.id, i.name, c.name, s.name, ss.quantity FROM item_details d JOIN items i ON d.item_id=i.id LEFT JOIN colors c ON d.color_id=c.id LEFT JOIN sizes s ON d.size_id=s.id LEFT JOIN store_stock ss ON (ss.item_detail_id=d.id AND ss.store_id=(SELECT id FROM stores WHERE name=?)) WHERE d.barcode=?"""
        res = self.db.fetch_one(sql, (store, code))
        if res:
            self.detail_id = res[0]
            stock = res[4] if res[4] else 0
            self.lbl_info.configure(text=f"{res[1]} ({res[2]} - {res[3]})\nStock in {store}: {stock}", text_color="white")
            self.ent_qty.focus()
        else:
            self.lbl_info.configure(text="Not Found", text_color="red")
            self.detail_id = None

    def do_transfer(self):
        if not self.detail_id: return
        try: qty = float(self.ent_qty.get())
        except: return messagebox.showerror("Error", "Invalid Qty")
        f, t = self.cb_from.get(), self.cb_to.get()
        if f == t: return messagebox.showerror("Error", "Stores must be different")
        s_f = self.db.fetch_one("SELECT id FROM stores WHERE name=?", (f,))[0]
        s_t = self.db.fetch_one("SELECT id FROM stores WHERE name=?", (t,))[0]
        cur = self.db.fetch_one("SELECT quantity FROM store_stock WHERE item_detail_id=? AND store_id=?", (self.detail_id, s_f))
        if not cur or cur[0] < qty: return messagebox.showerror("Error", "Insufficient Stock")
        self.db.execute("UPDATE store_stock SET quantity = quantity - ? WHERE item_detail_id=? AND store_id=?", (qty, self.detail_id, s_f))
        exists = self.db.fetch_one("SELECT 1 FROM store_stock WHERE item_detail_id=? AND store_id=?", (self.detail_id, s_t))
        if exists: self.db.execute("UPDATE store_stock SET quantity = quantity + ? WHERE item_detail_id=? AND store_id=?", (qty, self.detail_id, s_t))
        else: self.db.execute("INSERT INTO store_stock (item_detail_id, store_id, quantity) VALUES (?,?,?)", (self.detail_id, s_t, qty))
        messagebox.showinfo("Success", "Transfer Complete")
        self.lookup(None)
        if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
