
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import date
from app.database import DB

class VouchersPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.db = DB()
        
        # --- Header ---
        header = ctk.CTkFrame(self, height=50)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="سندات القبض والصرف (Vouchers)", font=("Arial", 20, "bold")).pack(side="left", padx=20)

        # --- Input Form ---
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=10, pady=5)
        
        # Row 1: Type & Safe
        r1 = ctk.CTkFrame(form_frame, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(r1, text="نوع السند:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        self.var_type = ctk.StringVar(value="Receipt")
        # Radio Buttons
        self.rb_in = ctk.CTkRadioButton(r1, text="سند قبض (Money In)", variable=self.var_type, value="Receipt", text_color="#27AE60", font=("Arial", 12, "bold"))
        self.rb_in.pack(side="left", padx=10)
        self.rb_out = ctk.CTkRadioButton(r1, text="سند صرف (Money Out)", variable=self.var_type, value="Payment", text_color="#C0392B", font=("Arial", 12, "bold"))
        self.rb_out.pack(side="left", padx=10)
        
        ctk.CTkLabel(r1, text="الخزينة:", font=("Arial", 12, "bold")).pack(side="left", padx=(40, 5))
        self.cb_safe = ctk.CTkComboBox(r1, width=200, font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_safe.pack(side="left", padx=5)
        
        
        # Row 2: Customer / Supplier Selection (Dynamic)
        r1_5 = ctk.CTkFrame(form_frame, fg_color="transparent")
        r1_5.pack(fill="x", padx=10, pady=5)
        
        self.lbl_party = ctk.CTkLabel(r1_5, text="العميل:", font=("Arial", 12, "bold"))
        self.lbl_party.pack(side="left", padx=5)
        
        self.cb_party = ctk.CTkComboBox(r1_5, width=300, font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_party.pack(side="left", padx=5)
        
        # Link radio buttons to update party list
        self.rb_in.configure(command=self.update_party_list)
        self.rb_out.configure(command=self.update_party_list)
        
        # Row 3: Amount & Description
        r2 = ctk.CTkFrame(form_frame, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(r2, text="المبلغ:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        self.ent_amount = ctk.CTkEntry(r2, width=120, font=("Arial", 12), placeholder_text="0.00")
        self.ent_amount.pack(side="left", padx=5)
        
        ctk.CTkLabel(r2, text="البيان / السبب:", font=("Arial", 12, "bold")).pack(side="left", padx=(20, 5))
        self.ent_desc = ctk.CTkEntry(r2, width=400, font=("Arial", 12), placeholder_text="مثال: إيراد متنوع / دفع إيجار / سلفة موظف...")
        self.ent_desc.pack(side="left", padx=5)
        
        ctk.CTkButton(r2, text="حفظ السند", command=self.save_voucher, font=("Arial", 13, "bold"), fg_color="#2980B9", width=150).pack(side="right", padx=20)

        # --- History Table ---
        ctk.CTkLabel(self, text="سجل المعاملات الأخيرة", font=("Arial", 14, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        
        self.tree = ttk.Treeview(self, columns=("ID", "Date", "Type", "Safe", "Amount", "Desc"), show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        cols = [("ID", 50), ("Date", 100), ("Type", 100), ("Safe", 150), ("Amount", 100), ("Desc", 300)]
        for c, w in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center" if c != "Desc" else "w")
            
        # Tag configuration for colors
        self.tree.tag_configure("in", foreground="green")
        self.tree.tag_configure("out", foreground="red")
        
        self.load_safes()
        self.update_party_list() # Load initial list
        self.load_history()

    def update_party_list(self):
        v_type = self.var_type.get()
        if v_type == "Receipt":
            self.lbl_party.configure(text="العميل (اختياري):")
            data = self.db.fetch_all("SELECT name FROM customers ORDER BY name")
        else:
            self.lbl_party.configure(text="المورد (اختياري):")
            data = self.db.fetch_all("SELECT name FROM suppliers ORDER BY name")
        
        vals = [d[0] for d in data]
        vals.insert(0, "") # Option for no party
        self.cb_party.configure(values=vals)
        self.cb_party.set("")

    def load_safes(self):
        safes = self.db.fetch_all("SELECT name FROM safes")
        if safes:
            self.cb_safe.configure(values=[s[0] for s in safes])
            self.cb_safe.set(safes[0][0])

    def load_history(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        sql = """
            SELECT v.id, v.date, v.voucher_type, s.name, v.amount, v.description 
            FROM vouchers v JOIN safes s ON v.safe_id = s.id 
            ORDER BY v.id DESC
        """
        for row in self.db.fetch_all(sql):
            # Show Type in Arabic logic for display
            v_type = "قبض (+)" if row[2] == "Receipt" else "صرف (-)"
            tag = "in" if row[2] == "Receipt" else "out"
            self.tree.insert("", "end", values=(row[0], row[1], v_type, row[3], row[4], row[5]), tags=(tag,))

    def save_voucher(self):
        try:
            amount = float(self.ent_amount.get())
            if amount <= 0: return messagebox.showerror("خطأ", "يجب أن يكون المبلغ أكبر من صفر")
        except: return messagebox.showerror("خطأ", "المبلغ غير صحيح")
        
        desc = self.ent_desc.get().strip()
        if not desc: return messagebox.showerror("خطأ", "ادخل البيان أو السبب")
        
        safe_name = self.cb_safe.get()
        safe_res = self.db.fetch_one("SELECT id FROM safes WHERE name=?", (safe_name,))
        if not safe_res: return messagebox.showerror("خطأ", "اختر الخزنة")
        safe_id = safe_res[0]
        
        v_type = self.var_type.get()
        party_name = self.cb_party.get()
        cust_id = None
        supp_id = None
        
        if party_name:
            if v_type == "Receipt":
                res = self.db.fetch_one("SELECT id FROM customers WHERE name=?", (party_name,))
                if res: cust_id = res[0]
            else:
                 res = self.db.fetch_one("SELECT id FROM suppliers WHERE name=?", (party_name,))
                 if res: supp_id = res[0]
        
        self.db.execute("INSERT INTO vouchers (date, voucher_type, safe_id, amount, description, customer_id, supplier_id) VALUES (?,?,?,?,?,?,?)",
                       (date.today(), v_type, safe_id, amount, desc, cust_id, supp_id))
        
        messagebox.showinfo("نجاح", "تم حفظ السند بنجاح")
        self.ent_amount.delete(0, "end")
        self.ent_desc.delete(0, "end")
        messagebox.showinfo("نجاح", "تم حفظ السند بنجاح")
        self.ent_amount.delete(0, "end")
        self.ent_desc.delete(0, "end")
        self.load_history()
        if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
