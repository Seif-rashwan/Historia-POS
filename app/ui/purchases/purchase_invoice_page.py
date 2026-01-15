
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import date
from app.database import DB
from app.database import DB
from app.config import COLS
from app.ui.sales.item_search_popup import ItemSearchPopup

class PurchaseInvoicePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.db = DB()
        self.cart_items = []
        self.editing_id = None
        
        # Setup validation command early (needed for entry fields below)
        self.vcmd = (self.register(self.validate_number), '%P')
        
        # Top Panel
        self.top_panel = ctk.CTkFrame(self, fg_color="gray20", corner_radius=10)
        self.top_panel.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(self.top_panel, text="فاتورة رقم:", text_color="gray", font=("Arial", 12)).grid(row=0, column=0, padx=10, pady=5)
        self.lbl_inv_num = ctk.CTkLabel(self.top_panel, text="جديد (تلقائي)", text_color="#16A085", font=("Arial", 12, "bold"))
        self.lbl_inv_num.grid(row=0, column=1, padx=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="التاريخ:", font=("Arial", 12)).grid(row=0, column=2, padx=10)
        self.lbl_date = ctk.CTkLabel(self.top_panel, text=str(date.today()), font=("Arial", 12, "bold"))
        self.lbl_date.grid(row=0, column=3, padx=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="المخزن:", text_color="#3B8ED0", font=("Arial", 12, "bold")).grid(row=0, column=4, padx=10)
        self.cb_store = ctk.CTkComboBox(self.top_panel, width=150, state="readonly", font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_store.grid(row=0, column=5, padx=5)
        
        # Manufacturing Switch
        self.var_is_manufacturing = ctk.BooleanVar(value=False)
        self.sw_manufacturing = ctk.CTkSwitch(self.top_panel, text="تصنيع خارجي", variable=self.var_is_manufacturing, command=self.toggle_manufacturing_mode, font=("Arial", 12, "bold"))
        self.sw_manufacturing.grid(row=0, column=6, padx=15)
        
        # Supplier Section (Standard)
        self.frm_std_supplier = ctk.CTkFrame(self.top_panel, fg_color="transparent")
        self.frm_std_supplier.grid(row=1, column=0, columnspan=7, sticky="ew")
        ctk.CTkLabel(self.frm_std_supplier, text="المورد:", font=("Arial", 12)).grid(row=0, column=0, padx=10, sticky="e", pady=5)
        self.ent_supplier_name = ctk.CTkEntry(self.frm_std_supplier, width=200, placeholder_text="اسم المورد", font=("Arial", 12))
        self.ent_supplier_name.grid(row=0, column=1, padx=5, pady=5)
        self.ent_supplier_name.bind("<Return>", self.search_supplier)
        
        self.phone_var = ctk.StringVar(value="+20")
        self.phone_var.trace("w", self.validate_phone)
        self.ent_supplier_phone = ctk.CTkEntry(self.frm_std_supplier, width=150, textvariable=self.phone_var, font=("Arial", 12))
        self.ent_supplier_phone.grid(row=0, column=2, padx=5)
        self.ent_supplier_phone.bind("<Return>", self.search_supplier)
        
        self.ent_supplier_addr = ctk.CTkEntry(self.frm_std_supplier, width=200, placeholder_text="العنوان", font=("Arial", 12))
        self.ent_supplier_addr.grid(row=0, column=3, padx=5)
        
        # Manufacturing Section (Initially Hidden)
        self.frm_mfg_supplier = ctk.CTkFrame(self.top_panel, fg_color="transparent")
        # Grid will be set in toggle
        
        ctk.CTkLabel(self.frm_mfg_supplier, text="مورد الخامات:", font=("Arial", 12, "bold")).grid(row=0, column=0, padx=5, pady=5)
        self.cb_mat_supplier = ctk.CTkComboBox(self.frm_mfg_supplier, width=180, font=("Arial", 12))
        self.cb_mat_supplier.grid(row=0, column=1, padx=5)
        
        ctk.CTkLabel(self.frm_mfg_supplier, text="تكلفة الخامات:", font=("Arial", 12)).grid(row=0, column=2, padx=5)
        self.ent_mat_cost = ctk.CTkEntry(self.frm_mfg_supplier, width=100, font=("Arial", 12))
        self.ent_mat_cost.grid(row=0, column=3, padx=5)
        self.ent_mat_cost.configure(validate="key", validatecommand=self.vcmd)  # FIX: Apply validation
        self.ent_mat_cost.bind("<KeyRelease>", self.calc_mfg_unit_cost)
        
        ctk.CTkLabel(self.frm_mfg_supplier, text="مورد التصنيع (المصنع):", font=("Arial", 12, "bold")).grid(row=1, column=0, padx=5, pady=5)
        self.cb_factory_supplier = ctk.CTkComboBox(self.frm_mfg_supplier, width=180, font=("Arial", 12))
        self.cb_factory_supplier.grid(row=1, column=1, padx=5)
        
        ctk.CTkLabel(self.frm_mfg_supplier, text="تكلفة التصنيع:", font=("Arial", 12)).grid(row=1, column=2, padx=5)
        self.ent_lab_cost = ctk.CTkEntry(self.frm_mfg_supplier, width=100, font=("Arial", 12))
        self.ent_lab_cost.grid(row=1, column=3, padx=5)
        self.ent_lab_cost.configure(validate="key", validatecommand=self.vcmd)  # FIX: Apply validation
        self.ent_lab_cost.bind("<KeyRelease>", self.calc_mfg_unit_cost)
        
        ctk.CTkLabel(self.frm_mfg_supplier, text="تكلفة الوحدة المحسوبة:", text_color="#E74C3C", font=("Arial", 12, "bold")).grid(row=0, column=4, rowspan=2, padx=10)
        self.lbl_mfg_unit_cost = ctk.CTkLabel(self.frm_mfg_supplier, text="0.00", text_color="#E74C3C", font=("Arial", 16, "bold"))
        self.lbl_mfg_unit_cost.grid(row=0, column=5, rowspan=2, padx=5)
        
        self.supplier_id = None
        
        # Payment Section
        self.mid_frame = ctk.CTkFrame(self, fg_color="gray25")
        self.mid_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(self.mid_frame, text="طريقة الدفع:", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        self.cb_pay_method = ctk.CTkComboBox(self.mid_frame, values=["نقدي", "تحويل بنكي", "أجل"], width=100, command=self.update_safes, font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_pay_method.pack(side="left", padx=5)
        self.cb_pay_method.set("نقدي")
        
        ctk.CTkLabel(self.mid_frame, text="الخزينة:", font=("Arial", 11)).pack(side="left", padx=5)
        self.cb_safe = ctk.CTkComboBox(self.mid_frame, width=140, font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_safe.pack(side="left", padx=5)
        
        # Grid Header
        self.grid_header = ctk.CTkFrame(self, height=35, fg_color="gray30")
        self.grid_header.pack(fill="x", padx=15, pady=(10,0))
        for text, width in [("الباركود", COLS["barcode"]), ("الصنف", COLS["name"]), ("اللون", COLS["color"]), 
                            ("المقاس", COLS["size"]), ("الكمية", COLS["qty"]), ("السعر", COLS["price"]), 
                            ("الإجمالي", COLS["total"]), ("حذف", COLS["action"])]:
            ctk.CTkLabel(self.grid_header, text=text, width=width, font=("Arial", 12, "bold")).pack(side="left", padx=2)
        
        # Scrollable Items Area
        self.scroll_frame = ctk.CTkScrollableFrame(self, height=250)
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Footer with totals
        self.footer = ctk.CTkFrame(self, height=180, fg_color="gray20", border_width=1, border_color="gray40")
        self.footer.pack(fill="x", padx=15, pady=10)
        
        self.f_left = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.f_left.pack(side="left", padx=20, pady=10, fill="y")
        
        def add_field(row, txt, var_name):
            ctk.CTkLabel(self.f_left, text=txt, font=("Arial", 12)).grid(row=row, column=0, sticky="e", padx=5, pady=2)
            e = ctk.CTkEntry(self.f_left, width=100, justify="right", font=("Arial", 12))
            e.grid(row=row, column=1, padx=5, pady=2)
            e.configure(state="readonly")
            setattr(self, var_name, e)
            return e
        
        add_field(0, "المجموع الفرعي:", "out_subtotal")
        add_field(1, "الخصم:", "out_discount")
        ctk.CTkLabel(self.f_left, text="الشحن (+):", font=("Arial", 12)).grid(row=2, column=0, sticky="e", padx=5)
        self.ent_shipping = ctk.CTkEntry(self.f_left, width=100, justify="right", font=("Arial", 12))
        self.ent_shipping.grid(row=2, column=1, padx=5, pady=2)
        self.ent_shipping.insert(0, "0")
        self.ent_shipping.bind("<KeyRelease>", self.grand_total)
        
        add_field(3, "الضريبة (+):", "out_tax")
        ctk.CTkLabel(self.f_left, text="الإجمالي النهائي:", font=("Arial", 14, "bold")).grid(row=4, column=0, sticky="e", padx=5, pady=10)
        self.out_net = ctk.CTkEntry(self.f_left, width=120, font=("Arial", 16, "bold"), text_color="#16A085", justify="right")
        self.out_net.grid(row=4, column=1, padx=5, pady=10)
        self.out_net.configure(state="readonly")
        
        self.f_mid = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.f_mid.pack(side="left", padx=20, pady=10, fill="y")
        ctk.CTkLabel(self.f_mid, text="الضريبة %", font=("Arial", 11)).pack(anchor="w")
        self.ent_tax_pct = ctk.CTkEntry(self.f_mid, width=80, placeholder_text="%", font=("Arial", 11))
        self.ent_tax_pct.pack(pady=(0, 10))
        self.ent_tax_pct.insert(0, "0")
        self.ent_tax_pct.bind("<KeyRelease>", self.grand_total)
        
        ctk.CTkLabel(self.f_mid, text="الخصم (ج.م)", font=("Arial", 11)).pack(anchor="w")
        self.ent_disc_pct = ctk.CTkEntry(self.f_mid, width=80, placeholder_text="ج.م", font=("Arial", 11))
        self.ent_disc_pct.pack(pady=(0, 10))
        self.ent_disc_pct.insert(0, "0")
        self.ent_disc_pct.bind("<KeyRelease>", self.grand_total)
        
        self.f_right = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.f_right.pack(side="right", padx=20, pady=10, fill="both", expand=True)
        ctk.CTkLabel(self.f_right, text="ملاحظات / ملاحظات:", font=("Arial", 12, "bold")).pack(anchor="w")
        self.txt_notes = ctk.CTkTextbox(self.f_right, height=60, border_width=1, font=("Arial", 12))
        self.txt_notes.pack(fill="x", pady=5)
        
        btn_row = ctk.CTkFrame(self.f_right, fg_color="transparent")
        btn_row.pack(fill="x", pady=5)
        ctk.CTkButton(btn_row, text="+ صنف (F2)", command=self.add_row, width=100, fg_color="#3B8ED0", font=("Arial", 12)).pack(side="left")
        self.btn_save = ctk.CTkButton(btn_row, text="حفظ (F5)", command=self.save_purchase, fg_color="#16A085", text_color="white", 
                                      font=("Arial", 14, "bold"), width=150)
        self.btn_save.pack(side="right")
        
        # Apply Validation
        self.ent_tax_pct.configure(validate="key", validatecommand=self.vcmd)
        self.ent_disc_pct.configure(validate="key", validatecommand=self.vcmd)
        self.ent_shipping.configure(validate="key", validatecommand=self.vcmd)

        self.load_data()
        self.add_row()
    
    def validate_number(self, P):
        """Validate numeric input - ONLY allows positive numbers (no negatives)"""
        if P == "": return True
        if P == "-": return False  # Block negative sign immediately
        try:
            val = float(P)
            return val >= 0  # Only accept non-negative values
        except ValueError:
            return False

    def open_search_popup(self, item_dict):
        def cb(barcode):
            item_dict['barcode'].delete(0, "end")
            item_dict['barcode'].insert(0, barcode)
            self.lookup(item_dict)
        ItemSearchPopup(self, cb)

    def validate_phone(self, *args):
        val = self.phone_var.get()
        # Filter non-digits except initial +
        clean = "+" + "".join([c for c in val if c.isdigit()])
        
        # Ensure starts with +20
        if not clean.startswith("+20"):
            self.phone_var.set("+20")
            return

        # Max Length: +20 (3 chars) + 10 digits = 13 chars
        if len(clean) > 13:
            self.phone_var.set(clean[:13])
        elif val != clean:
            self.phone_var.set(clean)
    
    def load_data(self):
        stores = self.db.fetch_all("SELECT name FROM stores")
        if stores:
            self.cb_store.configure(values=[s[0] for s in stores])
            self.cb_store.set(stores[0][0])
        self.update_safes("نقدي")
        self.load_suppliers_combo()

    def load_suppliers_combo(self):
        suppliers = self.db.fetch_all("SELECT name FROM suppliers ORDER BY name")
        vals = [s[0] for s in suppliers]
        if vals:
             self.cb_mat_supplier.configure(values=vals)
             self.cb_factory_supplier.configure(values=vals)
             self.cb_mat_supplier.set(vals[0])
             self.cb_factory_supplier.set(vals[0])

    def toggle_manufacturing_mode(self):
        if self.var_is_manufacturing.get():
            self.frm_std_supplier.grid_forget()
            self.frm_mfg_supplier.grid(row=1, column=0, columnspan=7, sticky="ew")
            # Clear standard cart prices? Maybe not.
        else:
            self.frm_mfg_supplier.grid_forget()
            self.frm_std_supplier.grid(row=1, column=0, columnspan=7, sticky="ew")
            
    def calc_mfg_unit_cost(self, e=None):
        try:
            mat = float(self.ent_mat_cost.get() or 0)
            lab = float(self.ent_lab_cost.get() or 0)
            total_qty = sum(float(item['qty'].get()) for item in self.cart_items)
            
            if total_qty > 0:
                unit_cost = (mat + lab) / total_qty
                self.lbl_mfg_unit_cost.configure(text=f"{unit_cost:.2f}")
            else:
                self.lbl_mfg_unit_cost.configure(text="0.00")
        except:
             self.lbl_mfg_unit_cost.configure(text="Err")
    
    def update_safes(self, choice):
        val = choice if isinstance(choice, str) else self.cb_pay_method.get()
        all_safes = [s[0] for s in self.db.fetch_all("SELECT name FROM safes")]
        filtered = []
        if val == "تحويل بنكي":
             filtered = [s for s in all_safes if "Bank" in s]
        elif val == "أجل":
             filtered = [] # No safe needed for deferred
        else:
             filtered = [s for s in all_safes if "Bank" not in s]
        
        self.cb_safe.configure(values=filtered if filtered else all_safes)
        if val == "أجل":
            self.cb_safe.set("")
            self.cb_safe.configure(state="disabled")
        else:
            self.cb_safe.configure(state="normal")
            if filtered: self.cb_safe.set(filtered[0])
    
    def search_supplier(self, e=None):
        name = self.ent_supplier_name.get().strip()
        phone = self.ent_supplier_phone.get().strip()
        res = None
        if len(phone) > 4:
            res = self.db.fetch_one("SELECT id, name, phone, address FROM suppliers WHERE phone=?", (phone,))
        if not res and name:
            res = self.db.fetch_one("SELECT id, name, phone, address FROM suppliers WHERE name LIKE ?", (f"%{name}%",))
        if res:
            self.supplier_id = res[0]
            self.ent_supplier_name.delete(0, "end")
            self.ent_supplier_name.insert(0, res[1])
            if self.focus_get() != self.ent_supplier_phone:
                self.phone_var.set(res[2] or "+20")
            self.ent_supplier_addr.delete(0, "end")
            self.ent_supplier_addr.insert(0, res[3] or "")
            if self.cart_items:
                self.cart_items[0]['barcode'].focus()
        else:
            self.supplier_id = None
    
    def add_row(self, e=None):
        row = ctk.CTkFrame(self.scroll_frame, height=35, fg_color="transparent")
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)
        
        entries = {}
        def mk(key, w, state="normal", ph=""):
            e = ctk.CTkEntry(row, width=w, height=28, state=state, placeholder_text=ph, font=("Arial", 11))
            e.pack(side="left", padx=2)
            entries[key] = e
            return e
        
        d = {"frame": row, "id": None}
        
        # Barcode + Search Button Container
        barcode_frame = ctk.CTkFrame(row, fg_color="transparent", width=COLS["barcode"])
        barcode_frame.pack(side="left", padx=2); barcode_frame.pack_propagate(False)
        
        d["barcode"] = ctk.CTkEntry(barcode_frame, width=COLS["barcode"]-35, height=28, placeholder_text="Scan", font=("Arial", 11))
        d["barcode"].pack(side="left", padx=2)
        
        # Search Button (Magnifying Glass)
        ctk.CTkButton(barcode_frame, text="🔍", width=30, height=28, fg_color="#3498DB", command=lambda: self.open_search_popup(d), font=("Arial", 12)).pack(side="left", padx=2)

        d["name"] = mk("name", COLS["name"], "readonly")
        d["color"] = mk("color", COLS["color"], "readonly")
        d["size"] = mk("size", COLS["size"], "readonly")
        d["qty"] = mk("qty", COLS["qty"])
        d["qty"].configure(validate="key", validatecommand=self.vcmd)
        d["qty"].insert(0, "1")
        d["price"] = mk("price", COLS["price"])
        d["price"].configure(validate="key", validatecommand=self.vcmd)
        lbl = ctk.CTkLabel(row, text="0.00", width=COLS["total"], font=("Arial", 11))
        lbl.pack(side="left", padx=2)
        d["total_lbl"] = lbl
        ctk.CTkButton(row, text="X", width=30, height=25, fg_color="#C0392B", command=lambda: self.del_row(d), font=("Arial", 10)).pack(side="left", padx=2)
        self.cart_items.append(d)
        d["barcode"].bind("<Return>", lambda x: self.lookup(d))
        d["qty"].bind("<KeyRelease>", lambda x: self.calc_row(d))
        d["price"].bind("<KeyRelease>", lambda x: self.calc_row(d))
        d["barcode"].focus()
    
    def lookup(self, d):
        code = d['barcode'].get().strip()
        sql = """SELECT d.id, i.name, c.name, s.name, d.buy_price 
                 FROM item_details d 
                 JOIN items i ON d.item_id=i.id 
                 LEFT JOIN colors c ON d.color_id=c.id 
                 LEFT JOIN sizes s ON d.size_id=s.id 
                 WHERE d.barcode=?"""
        res = self.db.fetch_one(sql, (code,))
        if res:
            d['id'] = res[0]
            for k, v in zip(["name", "color", "size"], [res[1], res[2], res[3]]):
                d[k].configure(state="normal")
                d[k].delete(0, "end")
                d[k].insert(0, str(v or "-"))
                d[k].configure(state="readonly")
            
            # ========================================
            # AUTO-FILL PRICE LOGIC
            # ========================================
            d['price'].delete(0, "end")
            
            if self.var_is_manufacturing.get():
                # Manufacturing Mode: Calculate unit cost from totals
                try:
                    mat_cost = float(self.ent_mat_cost.get() or 0)
                    lab_cost = float(self.ent_lab_cost.get() or 0)
                    total_qty = sum(float(item['qty'].get()) for item in self.cart_items if item.get('id'))
                    
                    if total_qty > 0:
                        calculated_unit_cost = (mat_cost + lab_cost) / total_qty
                        d['price'].insert(0, f"{calculated_unit_cost:.2f}")
                    else:
                        # Fallback if no quantity yet
                        d['price'].insert(0, "0")
                except (ValueError, ZeroDivisionError):
                    # Fallback to database price if calculation fails
                    d['price'].insert(0, str(res[4] or 0))
            else:
                # Standard Mode: Use database price
                d['price'].insert(0, str(res[4] or 0))
            
            self.calc_row(d)
            d['qty'].focus()
        else:
            d['barcode'].configure(text_color="red")
            messagebox.showerror("خطأ", "لم يتم العثور على الصنف!")
    
    def calc_row(self, d):
        try:
            # ========================================
            # MANUFACTURING MODE: Auto-update Price
            # ========================================
            if self.var_is_manufacturing.get():
                # Recalculate unit cost based on current totals and quantities
                try:
                    mat_cost = float(self.ent_mat_cost.get() or 0)
                    lab_cost = float(self.ent_lab_cost.get() or 0)
                    total_qty = sum(float(item['qty'].get()) for item in self.cart_items if item.get('id'))
                    
                    if total_qty > 0:
                        calculated_unit_cost = (mat_cost + lab_cost) / total_qty
                        # Update THIS row's price
                        d['price'].delete(0, "end")
                        d['price'].insert(0, f"{calculated_unit_cost:.2f}")
                except (ValueError, ZeroDivisionError):
                    pass  # Keep existing price if calculation fails
            
            # ========================================
            # Calculate Row Total
            # ========================================
            q = float(d['qty'].get())
            p = float(d['price'].get())
            d['total_lbl'].configure(text=f"{q*p:.2f}")
            
            # Update grand total and manufacturing unit cost label
            self.grand_total()
            if self.var_is_manufacturing.get():
                self.calc_mfg_unit_cost()
        except:
            pass
    
    def del_row(self, d):
        d['frame'].destroy()
        self.cart_items.remove(d)
        self.grand_total()
        if self.var_is_manufacturing.get():
            self.calc_mfg_unit_cost()
    
    def grand_total(self, e=None):
        try:
            sub = sum(float(i['total_lbl'].cget('text')) for i in self.cart_items)
            self.update_field(self.out_subtotal, sub)
            try:
                disc_val = float(self.ent_disc_pct.get())
            except:
                disc_val = 0.0
            self.update_field(self.out_discount, disc_val)
            after_disc = sub - disc_val
            try:
                tax_pct = float(self.ent_tax_pct.get())
            except:
                tax_pct = 0.0
            tax_val = after_disc * (tax_pct / 100)
            self.update_field(self.out_tax, tax_val)
            try:
                ship_val = float(self.ent_shipping.get())
            except:
                ship_val = 0.0
            net = after_disc + tax_val + ship_val
            self.update_field(self.out_net, net)
        except:
            pass
    
    def update_field(self, widget, value):
        widget.configure(state="normal")
        widget.delete(0, "end")
        widget.insert(0, f"{value:.2f}")
        widget.configure(state="readonly")
    
    def save_purchase(self):
        try:
            is_mfg = self.var_is_manufacturing.get()
            
            # Common Checks
            if not self.cart_items:
                return messagebox.showerror("خطأ", "السلة فارغة")
            
            store_name = self.cb_store.get()
            store_res = self.db.fetch_one("SELECT id FROM stores WHERE name=?", (store_name,))
            if not store_res: return messagebox.showerror("خطأ", "اختر المخزن")
            store_id = store_res[0]

            notes = self.txt_notes.get("1.0", "end").strip()
            today_date = date.today()

            # Helper for Supplies
            def get_supp_id(name, phone="", addr=""):
                res = self.db.fetch_one("SELECT id FROM suppliers WHERE name=?", (name,))
                if res: return res[0]
                return self.db.execute("INSERT INTO suppliers (name, phone, address) VALUES (?,?,?)", (name, phone, addr))

            if is_mfg:
                # --- Manufacturing Mode ---
                mat_name = self.cb_mat_supplier.get().strip()
                fac_name = self.cb_factory_supplier.get().strip()
                if not mat_name or not fac_name:
                    return messagebox.showerror("خطأ", "يجب تحديد مورد الخامات ومورد التصنيع")
                
                mat_supp_id = get_supp_id(mat_name)
                fac_supp_id = get_supp_id(fac_name)

                try:
                    mat_cost = float(self.ent_mat_cost.get() or 0)
                    lab_cost = float(self.ent_lab_cost.get() or 0)
                except ValueError: return messagebox.showerror("خطأ", "الأرقام غير صحيحة")

                # CRITICAL FIX: Block negative values that could corrupt WAC
                if mat_cost < 0 or lab_cost < 0:
                    return messagebox.showerror("خطأ", "التكلفة لا يمكن أن تكون سالبة!")

                if mat_cost + lab_cost <= 0:
                    return messagebox.showerror("خطأ", "يجب إدخال تكلفة الخامات أو التصنيع")

                total_qty = sum(float(i['qty'].get()) for i in self.cart_items)
                if total_qty <= 0: return messagebox.showerror("خطأ", "الكمية الكلية صفر!")

                unit_mat = mat_cost / total_qty
                unit_lab = lab_cost / total_qty
                unit_full = unit_mat + unit_lab

                # Transaction A: Material Purchase
                pid_mat = self.db.execute("""INSERT INTO purchases 
                    (date, supplier_id, net_total, store_id, payment_method, notes) 
                    VALUES (?, ?, ?, ?, 'نقدي', ?)""", 
                    (today_date, mat_supp_id, mat_cost, store_id, f"Mfg Mat: {notes}"))

                # Transaction B: Factory Purchase (LINKED to Material via parent_purchase_id)
                pid_fac = self.db.execute("""INSERT INTO purchases 
                    (date, supplier_id, net_total, store_id, payment_method, notes, parent_purchase_id) 
                    VALUES (?, ?, ?, ?, 'نقدي', ?, ?)""", 
                    (today_date, fac_supp_id, lab_cost, store_id, f"Mfg Factory: {notes}", pid_mat))

                # Process Items associated with Material Invoice
                for item in self.cart_items:
                    did = item['id']
                    qty = float(item['qty'].get())
                    
                    # Insert Detail (Linked to Material Invoice, with Material Price Portion)
                    # NOTE: We only track material cost in this invoice detail, but stock is updated fully.
                    self.db.execute("""INSERT INTO purchase_details 
                        (purchase_id, item_detail_id, qty, buy_price, total, returned_qty) 
                        VALUES (?, ?, ?, ?, ?, 0)""", 
                        (pid_mat, did, qty, unit_mat, qty * unit_mat))
                    
                    # WAC & Stock Update with FULL Cost
                    self.apply_wac_and_stock(did, qty, unit_full, store_id)

            else:
                # --- Standard Mode ---
                supp_name = self.ent_supplier_name.get().strip()
                if not supp_name: return messagebox.showerror("خطأ", "المورد مطلوب")
                
                # Phone Validation
                phone = self.phone_var.get()
                if len(phone) != 13:
                    return messagebox.showerror("خطأ", "رقم الهاتف غير صحيح")
                
                supp_id = get_supp_id(supp_name, phone, self.ent_supplier_addr.get().strip())
                self.db.execute("UPDATE suppliers SET phone=?, address=? WHERE id=?", 
                                (phone, self.ent_supplier_addr.get(), supp_id))
                
                # Totals
                net = float(self.out_net.get() or 0)
                tax = float(self.ent_tax_pct.get() or 0)
                disc = float(self.ent_disc_pct.get() or 0)
                ship = float(self.ent_shipping.get() or 0)
                
                pid = self.db.execute("""INSERT INTO purchases 
                    (date, supplier_id, net_total, store_id, payment_method, 
                     tax_percent, discount_percent, discount_value, shipping_cost, notes, paid_amount) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                    (today_date, supp_id, net, store_id, self.cb_pay_method.get(), 
                     tax, disc, disc, ship, notes, net if self.cb_pay_method.get() != "أجل" else 0))
                
                for item in self.cart_items:
                    did = item['id']
                    qty = float(item['qty'].get())
                    price = float(item['price'].get())
                    
                    self.db.execute("""INSERT INTO purchase_details 
                        (purchase_id, item_detail_id, qty, buy_price, total, returned_qty) 
                        VALUES (?, ?, ?, ?, ?, 0)""", 
                        (pid, did, qty, price, qty * price))
                    
                    # WAC & Stock Update
                    self.apply_wac_and_stock(did, qty, price, store_id)

            messagebox.showinfo("نجاح", "تم حفظ الفاتورة بنجاح")
            if hasattr(self.controller, 'refresh_views'):
                 self.controller.refresh_views()
            self.reset_form()

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء الحفظ:\n{e}")

    def apply_wac_and_stock(self, item_id, new_qty, new_cost, store_id):
        """
        Apply Weighted Average Cost and update stock.
        Formula: WAC = ((old_qty * old_cost) + (new_qty * new_cost)) / (old_qty + new_qty)
        
        CRITICAL: This must fetch CURRENT stock BEFORE any updates to calculate correct WAC.
        """
        try:
            # ==========================================
            # STEP 1: FETCH CURRENT STATE (BEFORE UPDATES)
            # ==========================================
            
            # Fetch from store_stock (primary source)
            res_store = self.db.fetch_one(
                "SELECT SUM(quantity) FROM store_stock WHERE item_detail_id=?", 
                (item_id,)
            )
            old_qty_store = res_store[0] if res_store and res_store[0] is not None else 0
            
            # Fetch from item_details (backup/validation)
            res_item = self.db.fetch_one(
                "SELECT buy_price, stock_qty FROM item_details WHERE id=?", 
                (item_id,)
            )
            
            if not res_item:
                raise ValueError(f"Item ID {item_id} not found in database!")
            
            old_cost = res_item[0] if res_item[0] is not None else 0
            old_qty_master = res_item[1] if res_item[1] is not None else 0
            
            # Determine which quantity to use for WAC calculation
            # Priority: store_stock > item_details.stock_qty
            old_qty = old_qty_store if old_qty_store > 0 else old_qty_master
            
            # ==========================================
            # STEP 2: CALCULATE WAC
            # ==========================================
            
            if old_qty > 0 and old_cost > 0:
                # Standard WAC formula
                total_value = (old_qty * old_cost) + (new_qty * new_cost)
                total_qty = old_qty + new_qty
                final_cost = total_value / total_qty
                
                # FIX: Round to 2 decimal places (Egyptian Piasters standard) to prevent floating-point drift
                final_cost = round(final_cost, 2)
                
                # DEBUG LOGGING
                print(f"\n{'='*60}")
                print(f"🔍 WAC CALCULATION - Item ID: {item_id}")
                print(f"{'='*60}")
                print(f"📊 BEFORE:")
                print(f"   Stock (store_stock): {old_qty_store} units")
                print(f"   Stock (item_details): {old_qty_master} units")
                print(f"   Using for WAC: {old_qty} units")
                print(f"   Current Cost: {old_cost:.2f}")
                print(f"   Current Value: {old_qty * old_cost:.2f}")
                print(f"\n📦 NEW PURCHASE:")
                print(f"   Quantity: {new_qty} units")
                print(f"   Unit Cost: {new_cost:.2f}")
                print(f"   Total Value: {new_qty * new_cost:.2f}")
                print(f"\n🧮 WAC FORMULA:")
                print(f"   ({old_qty} × {old_cost:.2f}) + ({new_qty} × {new_cost:.2f})")
                print(f"   = {old_qty * old_cost:.2f} + {new_qty * new_cost:.2f}")
                print(f"   = {total_value:.2f}")
                print(f"   ÷ ({old_qty} + {new_qty})")
                print(f"   = {total_value:.2f} ÷ {total_qty}")
                print(f"   = {final_cost:.2f}")
                print(f"\n✅ FINAL WEIGHTED AVERAGE COST: {final_cost:.2f}")
                
            elif old_qty > 0 and old_cost == 0:
                # Has stock but no cost (unusual, but handle it)
                final_cost = round(new_cost, 2)
                print(f"\n⚠️  WARNING - Item ID {item_id}:")
                print(f"   Has stock ({old_qty} units) but ZERO cost!")
                print(f"   Setting cost to NEW COST: {new_cost:.2f}")
                
            else:
                # First purchase (no existing stock)
                final_cost = round(new_cost, 2)
                print(f"\n📍 FIRST PURCHASE - Item ID {item_id}:")
                print(f"   No existing stock (old_qty={old_qty})")
                print(f"   Setting initial cost: {new_cost:.2f}")
            
            # ==========================================
            # STEP 3: UPDATE DATABASE
            # ==========================================
            
            # Update master cost
            self.db.execute(
                "UPDATE item_details SET buy_price=? WHERE id=?", 
                (final_cost, item_id)
            )
            print(f"✅ Updated item_details.buy_price = {final_cost:.2f}")
            
            # Update or insert store_stock
            exists = self.db.fetch_one(
                "SELECT quantity FROM store_stock WHERE item_detail_id=? AND store_id=?", 
                (item_id, store_id)
            )
            
            if exists:
                old_store_qty = exists[0]
                self.db.execute(
                    "UPDATE store_stock SET quantity = quantity + ? WHERE item_detail_id=? AND store_id=?", 
                    (new_qty, item_id, store_id)
                )
                print(f"✅ Updated store_stock: {old_store_qty} + {new_qty} = {old_store_qty + new_qty} units")
            else:
                self.db.execute(
                    "INSERT INTO store_stock (item_detail_id, store_id, quantity) VALUES (?,?,?)", 
                    (item_id, store_id, new_qty)
                )
                print(f"✅ Inserted new store_stock record: {new_qty} units")
            
            # Sync item_details.stock_qty
            self.db.execute(
                "UPDATE item_details SET stock_qty = stock_qty + ? WHERE id=?", 
                (new_qty, item_id)
            )
            print(f"✅ Synced item_details.stock_qty: +{new_qty} units")
            
            # ==========================================
            # STEP 4: VERIFICATION
            # ==========================================
            
            # Verify the update
            verify = self.db.fetch_one(
                "SELECT buy_price, stock_qty FROM item_details WHERE id=?", 
                (item_id,)
            )
            verify_store = self.db.fetch_one(
                "SELECT SUM(quantity) FROM store_stock WHERE item_detail_id=?", 
                (item_id,)
            )
            
            print(f"\n📋 VERIFICATION:")
            print(f"   Master Cost: {verify[0]:.2f}")
            print(f"   Master Stock: {verify[1]}")
            print(f"   Store Stock: {verify_store[0]}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n❌ ERROR in apply_wac_and_stock:")
            print(f"   Item ID: {item_id}")
            print(f"   Error: {str(e)}")
            raise e

    def reset_form(self):
        self.editing_id = None
        self.lbl_inv_num.configure(text="جديد (تلقائي)", text_color="#16A085")
        self.btn_save.configure(text="حفظ (F5)", fg_color="#16A085")
        
        self.ent_supplier_name.delete(0, "end")
        self.ent_supplier_phone.delete(0, "end"); self.phone_var.set("+20")
        self.ent_supplier_addr.delete(0, "end")
        self.ent_tax_pct.delete(0, "end"); self.ent_tax_pct.insert(0, "0")
        self.ent_disc_pct.delete(0, "end"); self.ent_disc_pct.insert(0, "0")
        self.ent_shipping.delete(0, "end"); self.ent_shipping.insert(0, "0")
        self.txt_notes.delete("1.0", "end")
        self.supplier_id = None
        
        self.ent_mat_cost.delete(0, "end")
        self.ent_lab_cost.delete(0, "end")
        self.lbl_mfg_unit_cost.configure(text="0.00")
        self.var_is_manufacturing.set(False)
        self.toggle_manufacturing_mode()
        
        for item in self.cart_items:
            item['frame'].destroy()
        self.cart_items = []
        self.add_row()
        self.grand_total()
