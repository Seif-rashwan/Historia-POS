
import customtkinter as ctk
from tkinter import messagebox
from datetime import date
import sqlite3
import os
import urllib.parse
import tempfile
import webbrowser
import subprocess
from tkinter import filedialog
from app.config_manager import ConfigManager

from app.database import DB
from app.config import COLS
from app.utils import fix_text, WHATSAPP_AVAILABLE, REPORTLAB_AVAILABLE
from .item_search_popup import ItemSearchPopup
from app.ui.sales.design_gallery_popup import DesignGalleryPopup

# Conditional Import for ReportLab
if REPORTLAB_AVAILABLE:
    from app.utils import (
        SimpleDocTemplate, A4, A5, Table, TableStyle, Paragraph, Spacer, 
        colors, getSampleStyleSheet, ParagraphStyle, pdfmetrics, TTFont, RLImage as Image
    )

class OrderPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.db = DB()
        self.cart_items = []
        self.editing_id = None
        
        # Flag to track if user manually typed in Paid field
        self.paid_manually_edited = False
        
        # For WhatsApp integration
        self.last_saved_invoice_id = None
        self.last_saved_customer_phone = None

        # --- Top Panel ---
        self.top_panel = ctk.CTkFrame(self, fg_color="gray20", corner_radius=10)
        self.top_panel.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(self.top_panel, text="INVOICE NO:", text_color="gray", font=("Arial", 12)).grid(row=0, column=0, padx=10, pady=5)
        self.lbl_inv_num = ctk.CTkLabel(self.top_panel, text="New (Auto)", text_color="#2CC985", font=("Arial", 12, "bold"))
        self.lbl_inv_num.grid(row=0, column=1, padx=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="DATE:", font=("Arial", 12)).grid(row=0, column=2, padx=10)
        self.lbl_date = ctk.CTkLabel(self.top_panel, text=str(date.today()), font=("Arial", 12, "bold"))
        self.lbl_date.grid(row=0, column=3, padx=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="STORE:", text_color="#3B8ED0", font=("Arial", 12, "bold")).grid(row=0, column=4, padx=10)
        self.cb_store = ctk.CTkComboBox(self.top_panel, width=150, state="readonly", font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_store.grid(row=0, column=5, padx=5)
        
        ctk.CTkLabel(self.top_panel, text="Customer:", font=("Arial", 12)).grid(row=1, column=0, padx=10, sticky="e")
        self.ent_cust_name = ctk.CTkEntry(self.top_panel, width=150, placeholder_text="Name", font=("Arial", 12))
        self.ent_cust_name.grid(row=1, column=1, padx=5, pady=5)
        self.ent_cust_name.bind("<Return>", self.search_customer)
        
        self.phone_var = ctk.StringVar(value="+20")
        self.phone_var.trace("w", self.validate_phone)
        self.ent_cust_phone = ctk.CTkEntry(self.top_panel, width=130, textvariable=self.phone_var, font=("Arial", 12))
        self.ent_cust_phone.grid(row=1, column=2, padx=5)
        self.ent_cust_phone.bind("<Return>", self.search_customer)
        
        self.ent_cust_addr = ctk.CTkEntry(self.top_panel, width=200, placeholder_text="Address", font=("Arial", 12))
        self.ent_cust_addr.grid(row=1, column=3, padx=5)
        
        ctk.CTkLabel(self.top_panel, text="Channel:", text_color="#E67E22", font=("Arial", 12)).grid(row=1, column=4, padx=5)
        self.cb_channel = ctk.CTkComboBox(self.top_panel, width=130, font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_channel.grid(row=1, column=5, padx=5)
        self.cb_channel.set("")
        self.cust_id = None

        # --- Mid Panel ---
        self.mid_frame = ctk.CTkFrame(self, fg_color="gray25")
        self.mid_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(self.mid_frame, text="PAYMENT:", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        self.cb_pay_method = ctk.CTkComboBox(self.mid_frame, values=["Cash", "Visa", "Instapay"], width=100, command=self.update_safes, font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_pay_method.pack(side="left", padx=5)
        self.cb_pay_method.set("Cash")
        ctk.CTkLabel(self.mid_frame, text="SAFE:", font=("Arial", 11)).pack(side="left", padx=5)
        self.cb_safe = ctk.CTkComboBox(self.mid_frame, width=140, font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_safe.pack(side="left", padx=5)
        ctk.CTkLabel(self.mid_frame, text="|  DELIVERY:", font=("Arial", 11, "bold")).pack(side="left", padx=10)
        self.delivery_var = ctk.StringVar(value="Delegate")
        ctk.CTkRadioButton(self.mid_frame, text="Delegate", variable=self.delivery_var, value="Delegate", command=self.toggle_delivery, width=80, font=("Arial", 12)).pack(side="left", padx=5)
        ctk.CTkRadioButton(self.mid_frame, text="Shipping", variable=self.delivery_var, value="Shipping", command=self.toggle_delivery, width=80, font=("Arial", 12)).pack(side="left", padx=5)
        self.cb_delivery_agent = ctk.CTkComboBox(self.mid_frame, width=150, font=("Arial", 12), dropdown_font=("Arial", 12))
        self.cb_delivery_agent.pack(side="left", padx=5)

        # --- Grid Header ---
        self.grid_header = ctk.CTkFrame(self, height=35, fg_color="gray30")
        self.grid_header.pack(fill="x", padx=15, pady=(10,0))
        for text, width in [("Barcode", COLS["barcode"]), ("Item Name", COLS["name"]), ("Color", COLS["color"]), ("Size", COLS["size"]), ("Design/Print", COLS["design"]), ("Qty", COLS["qty"]), ("Price", COLS["price"]), ("Total", COLS["total"]), ("Del", COLS["action"])]:
            ctk.CTkLabel(self.grid_header, text=text, width=width, font=("Arial", 12, "bold")).pack(side="left", padx=2)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, height=200)
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=5)

        # --- Footer ---
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
            
        add_field(0, "Subtotal:", "out_subtotal")
        ctk.CTkLabel(self.f_left, text="Shipping (+):", font=("Arial", 12)).grid(row=1, column=0, sticky="e", padx=5)
        self.ent_shipping = ctk.CTkEntry(self.f_left, width=100, justify="right", font=("Arial", 12))
        self.ent_shipping.grid(row=1, column=1, padx=5, pady=2)
        self.ent_shipping.insert(0, "0")
        self.ent_shipping.bind("<KeyRelease>", self.grand_total)
        ctk.CTkLabel(self.f_left, text="NET TOTAL:", font=("Arial", 14, "bold")).grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.out_net = ctk.CTkEntry(self.f_left, width=120, font=("Arial", 16, "bold"), text_color="#2CC985", justify="right")
        self.out_net.grid(row=2, column=1, padx=5, pady=5)
        self.out_net.configure(state="readonly")

        self.f_mid = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.f_mid.pack(side="left", padx=20, pady=10, fill="y")
        ctk.CTkLabel(self.f_mid, text="Discount (LE):").pack(anchor="w")
        self.ent_disc_pct = ctk.CTkEntry(self.f_mid, width=100, font=("Arial", 12))
        self.ent_disc_pct.pack(pady=2)
        self.ent_disc_pct.insert(0, "0")
        self.ent_disc_pct.bind("<KeyRelease>", self.grand_total)
        
        # PAID Amount Field
        ctk.CTkLabel(self.f_mid, text="PAID (المدفوع):", font=("Arial", 12, "bold"), text_color="#F39C12").pack(anchor="w", pady=(10,0))
        self.ent_paid = ctk.CTkEntry(self.f_mid, width=100, font=("Arial", 14, "bold"))
        self.ent_paid.pack(pady=2)
        self.ent_paid.insert(0, "0")
        
        # Events for Paid field logic
        self.ent_paid.bind("<Key>", self.on_paid_manual_edit)
        self.ent_paid.bind("<KeyRelease>", self.calc_remaining)
        
        self.lbl_remaining = ctk.CTkLabel(self.f_mid, text="Remaining: 0.00", font=("Arial", 12, "bold"), text_color="#E74C3C")
        self.lbl_remaining.pack(pady=5)

        self.f_right = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.f_right.pack(side="right", padx=20, pady=10, fill="both", expand=True)
        ctk.CTkLabel(self.f_right, text="Notes:", font=("Arial", 12)).pack(anchor="w")
        self.txt_notes = ctk.CTkTextbox(self.f_right, height=50, border_width=1, font=("Arial", 12))
        self.txt_notes.pack(fill="x", pady=5)
        
        btn_row = ctk.CTkFrame(self.f_right, fg_color="transparent")
        btn_row.pack(fill="x", pady=5)
        ctk.CTkButton(btn_row, text="+ Item (F2)", command=self.add_row, width=80, fg_color="#3B8ED0", font=("Arial", 12)).pack(side="left")
        self.btn_save = ctk.CTkButton(btn_row, text="SAVE (F5)", command=self.save_invoice, fg_color="#2CC985", text_color="black", font=("Arial", 14, "bold"), width=120)
        self.btn_save.pack(side="right")
        
        self.vcmd = (self.register(self.validate_number), '%P')
        
        # Apply validation
        self.ent_disc_pct.configure(validate="key", validatecommand=self.vcmd)
        self.ent_paid.configure(validate="key", validatecommand=self.vcmd)
        self.ent_shipping.configure(validate="key", validatecommand=self.vcmd)

        self.load_data()
        self.add_row()

    def validate_number(self, P):
        if P == "": return True
        try:
            float(P)
            return True
        except ValueError:
            return False

    # --- Paid Logic ---
    def on_paid_manual_edit(self, event):
        # Once user types, we stop auto-filling
        self.paid_manually_edited = True

    def open_search_popup(self, item_dict):
        def cb(barcode):
            item_dict['barcode'].delete(0, "end")
            item_dict['barcode'].insert(0, barcode)
            self.lookup(item_dict)
        ItemSearchPopup(self, cb)

    def validate_rules(self, store_id):
        error_messages = []
        has_hoodie = False
        has_hd_design = False
        for item in self.cart_items:
            if item['id']:
                barcode = item['barcode'].get().strip().upper()
                name = item['name'].get()
                try: req_qty = float(item['qty'].get())
                except: return False, f"Invalid Qty for {name}"
                if barcode.startswith("HD"): has_hd_design = True
                else: has_hoodie = True
                if barcode.startswith("HD"): continue 
                res = self.db.fetch_one("SELECT quantity FROM store_stock WHERE item_detail_id=? AND store_id=?", (item['id'], store_id))
                current_stock = res[0] if res else 0
                if self.editing_id:
                    old = self.db.fetch_one("SELECT qty FROM invoice_details WHERE invoice_id=? AND item_detail_id=?", (self.editing_id, item['id']))
                    if old: current_stock += old[0]
                if current_stock < req_qty:
                    error_messages.append(f"• {name}: Req {int(req_qty)} / Avail {int(current_stock)}")
        if has_hd_design and not has_hoodie: return False, "❌ خطأ: لا يمكن بيع تصميم (HD) بدون وجود هودي في الفاتورة!"
        if error_messages: return False, "Insufficient Stock for:\n" + "\n".join(error_messages)
        return True, None

    def save_invoice(self):
        try:
            cust = self.ent_cust_name.get()
            if not cust: return messagebox.showerror("Error", "Customer name required")
            if not self.cart_items: return messagebox.showerror("Error", "Invoice is empty")
            store_res = self.db.fetch_one("SELECT id FROM stores WHERE name=?", (self.cb_store.get(),))
            if not store_res: return messagebox.showerror("Error", "Select a store")
            store_id = store_res[0]
            valid, msg = self.validate_rules(store_id)
            if not valid: return messagebox.showerror("Warning", msg)
            safe_id = None
            if self.cb_safe.get():
                safe_res = self.db.fetch_one("SELECT id FROM safes WHERE name=?", (self.cb_safe.get(),))
                if safe_res: safe_id = safe_res[0]
            if not self.cust_id:
                self.cust_id = self.db.execute("INSERT INTO customers (name, phone, address) VALUES (?,?,?)", (cust, self.phone_var.get(), self.ent_cust_addr.get()))
            else:
                 self.db.execute("UPDATE customers SET phone=?, address=? WHERE id=?", (self.phone_var.get(), self.ent_cust_addr.get(), self.cust_id))
            
            net = float(self.out_net.get())
            disc_val = float(self.ent_disc_pct.get() or 0)
            ship = float(self.ent_shipping.get() or 0)
            try: paid = float(self.ent_paid.get())
            except: paid = 0.0
            remaining = net - paid
            notes = self.txt_notes.get("1.0", "end").strip()
            
            inv_id = self.editing_id
            if inv_id:
                old_store_id = self.db.fetch_one("SELECT store_id FROM invoices WHERE id=?", (inv_id,))[0]
                old_items = self.db.fetch_all("SELECT item_detail_id, qty FROM invoice_details WHERE invoice_id=?", (inv_id,))
                for did, qty in old_items:
                    self.db.execute("UPDATE store_stock SET quantity = quantity + ? WHERE item_detail_id=? AND store_id=?", (qty, did, old_store_id))
                self.db.execute("DELETE FROM invoice_details WHERE invoice_id=?", (inv_id,))
                self.db.execute("""UPDATE invoices SET date=?, customer_id=?, net_total=?, paid_amount=?, remaining_amount=?, store_id=?, safe_id=?, payment_method=?, delegate_name=?, channel=?, discount_percent=?, shipping_cost=?, notes=? WHERE id=?""", 
                                (date.today(), self.cust_id, net, paid, remaining, store_id, safe_id, self.cb_pay_method.get(), self.cb_delivery_agent.get(), self.cb_channel.get(), disc_val, ship, notes, inv_id))
            else:
                inv_id = self.db.execute("""INSERT INTO invoices (date, customer_id, net_total, paid_amount, remaining_amount, store_id, safe_id, payment_method, delegate_name, channel, discount_percent, shipping_cost, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
                                         (date.today(), self.cust_id, net, paid, remaining, store_id, safe_id, self.cb_pay_method.get(), self.cb_delivery_agent.get(), self.cb_channel.get(), disc_val, ship, notes))
            # Find Central "Main Stock" ID for HD Designs
            main_stock_res = self.db.fetch_one("SELECT id FROM stores WHERE name LIKE 'Main Stock%' ORDER BY id ASC")
            # Default to ID 1 if not found, as per business logic (Raw materials in Main)
            main_stock_id = main_stock_res[0] if main_stock_res else 1

            for item in self.cart_items:
                if item['id']:
                    qty = float(item['qty'].get()); price = float(item['price'].get())
                    
                    # Store Design Name in item_note if selected
                    design_name = ""
                    design_val = item.get("design").get().strip() # Combobox value
                    hd_key = None
                    
                    if design_val and design_val != "Plain / سادة":
                         # Check if it's a full key or a barcode
                         if hasattr(self, 'hd_map') and design_val in self.hd_map:
                             hd_key = design_val
                         elif hasattr(self, 'hd_barcode_lookup') and design_val.upper() in self.hd_barcode_lookup:
                             hd_key = self.hd_barcode_lookup[design_val.upper()]
                    
                    if hd_key and hasattr(self, 'hd_map'):
                         raw_name = self.hd_map[hd_key]["name"]
                         design_name = f" [{raw_name}]"
                    
                    # ========================================
                    # FETCH CURRENT COST (For Profit Calculation)
                    # ========================================
                    current_cost = self.db.fetch_one("SELECT buy_price FROM item_details WHERE id=?", (item['id'],))
                    cost_at_sale_val = current_cost[0] if current_cost else 0
                    
                    # Insert into invoice_details with item_note AND cost_at_sale
                    self.db.execute("""INSERT INTO invoice_details 
                        (invoice_id, item_detail_id, qty, price, total, item_note, cost_at_sale) 
                        VALUES (?,?,?,?,?,?,?)""", 
                        (inv_id, item['id'], qty, price, qty*price, design_name, cost_at_sale_val))
                    
                    # Deduct Main Item Stock (From Sales Store)
                    exists = self.db.fetch_one("SELECT 1 FROM store_stock WHERE item_detail_id=? AND store_id=?", (item['id'], store_id))
                    if exists: self.db.execute("UPDATE store_stock SET quantity = quantity - ? WHERE item_detail_id=? AND store_id=?", (qty, item['id'], store_id))
                    else: self.db.execute("INSERT INTO store_stock (item_detail_id, store_id, quantity) VALUES (?,?,?)", (item['id'], store_id, -qty))
                    
                    # Deduct HD Design Stock (ALWAYS From Main Stock)
                    if hd_key and hasattr(self, 'hd_map'):
                        hd_id = self.hd_map[hd_key]["id"]
                        # Check exist in Main Stock
                        hd_exists = self.db.fetch_one("SELECT 1 FROM store_stock WHERE item_detail_id=? AND store_id=?", (hd_id, main_stock_id))
                        if hd_exists: self.db.execute("UPDATE store_stock SET quantity = quantity - ? WHERE item_detail_id=? AND store_id=?", (qty, hd_id, main_stock_id))
                        else: self.db.execute("INSERT INTO store_stock (item_detail_id, store_id, quantity) VALUES (?,?,?)", (hd_id, main_stock_id, -qty))
            
            self.last_saved_invoice_id = inv_id
            self.last_saved_customer_phone = self.phone_var.get()
            
            if WHATSAPP_AVAILABLE and self.last_saved_customer_phone and self.last_saved_customer_phone.strip() != "+20":
                msg = messagebox.askyesno("Saved", f"Invoice #{inv_id} Saved!\nPaid: {paid} | Due: {remaining}\n\nSend via WhatsApp?")
                self.generate_invoice_pdf(inv_id, open_whatsapp=msg)
            else:
                self.generate_invoice_pdf(inv_id, open_whatsapp=False)
            
            self.controller.refresh_views()
            self.reset_form()
        except sqlite3.IntegrityError as e:
            err_msg = str(e)
            if "customers.phone" in err_msg or "UNIQUE constraint failed" in err_msg:
                messagebox.showerror("Error", "Phone number already registered!\n(Duplicate Phone Number)")
            else:
                messagebox.showerror("Error", f"Database Error: {err_msg}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def grand_total(self, e=None):
        try:
            sub = sum(float(i['total_lbl'].cget('text')) for i in self.cart_items)
            self.update_field(self.out_subtotal, sub)
            try: disc_val = float(self.ent_disc_pct.get())
            except: disc_val = 0.0
            try: ship_val = float(self.ent_shipping.get())
            except: ship_val = 0.0
            net = (sub - disc_val) + ship_val
            self.update_field(self.out_net, net)
            
            if not self.paid_manually_edited:
                self.ent_paid.delete(0, "end")
                self.ent_paid.insert(0, f"{net:.2f}")
            
            self.calc_remaining()
        except: pass

    def calc_remaining(self, e=None):
        try:
            net = float(self.out_net.get())
            try: paid = float(self.ent_paid.get())
            except: paid = 0.0
            rem = net - paid
            self.lbl_remaining.configure(text=f"Remaining: {rem:.2f}")
            if rem > 0.01: self.lbl_remaining.configure(text_color="#E74C3C")
            else: self.lbl_remaining.configure(text_color="#27AE60")
        except: pass

    def update_field(self, widget, value):
        widget.configure(state="normal"); widget.delete(0, "end"); widget.insert(0, f"{value:.2f}"); widget.configure(state="readonly")
    
    def generate_invoice_pdf(self, invoice_id, open_whatsapp=False):
        try:
            if not REPORTLAB_AVAILABLE:
                messagebox.showerror("Error", "ReportLab library not installed")
                return
            
            # Ensure directory exists
            cm = ConfigManager()
            save_dir = cm.get_save_dir()
            if not save_dir or not os.path.exists(save_dir):
                messagebox.showinfo("Settings", "Please select a folder to save invoices (will be default)")
                save_dir = filedialog.askdirectory(title="Select Invoice Folder")
                if save_dir:
                    cm.set_save_dir(save_dir)
                else:
                    return # User cancelled
            
            # Helper to fetch data (unchanged)
            sql = """SELECT i.date, c.name, c.phone, c.address, s.name, i.payment_method, i.delegate_name, i.discount_percent, i.tax_percent, i.shipping_cost, i.notes, i.paid_amount, i.remaining_amount, i.net_total FROM invoices i LEFT JOIN customers c ON i.customer_id=c.id LEFT JOIN stores s ON i.store_id=s.id WHERE i.id=?"""
            inv_data = self.db.fetch_one(sql, (invoice_id,))
            if not inv_data: 
                messagebox.showerror("Error", "Invoice not found")
                return

            cust_name = inv_data[1] or "Client"
            safe_cust_name = "".join([c for c in cust_name if c.isalnum() or c in (' ', '_', '-')]).strip()
            pdf_filename = f"Inv_{invoice_id}_{safe_cust_name}.pdf"
            pdf_path = os.path.join(save_dir, pdf_filename)

            # Updated query to fetch item_note
            items = self.db.fetch_all("""SELECT d.barcode, i.name, c.name, s.name, id.qty, id.price, id.total, id.item_note FROM invoice_details id JOIN item_details d ON id.item_detail_id = d.id JOIN items i ON d.item_id = i.id LEFT JOIN colors c ON d.color_id = c.id LEFT JOIN sizes s ON d.size_id = s.id WHERE id.invoice_id = ?""", (invoice_id,))
            
            # --- Professional PDF Design using ReportLab (A5) ---
            doc = SimpleDocTemplate(pdf_path, pagesize=A5, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
            elements = []
            
            # Styles
            styles = getSampleStyleSheet()
            font_name = 'Helvetica' # English Only
            title_style = ParagraphStyle(name='TitleStyle', fontName='Helvetica-Bold', fontSize=16, leading=20, alignment=1, textColor=colors.HexColor("#2C3E50"))
            normal_center = ParagraphStyle(name='NormalCenter', fontName='Helvetica', fontSize=10, alignment=1, textColor=colors.black)
            normal_right = ParagraphStyle(name='NormalRight', fontName='Helvetica', fontSize=9, alignment=2)
            normal_left = ParagraphStyle(name='NormalLeft', fontName='Helvetica', fontSize=9, alignment=0)
            
            # --- 1. Header Section ---
            # Logo (Left) | Invoice Info (Right) - 2 Columns
            logo_path = os.path.join("assets", "logo.png")
            logo_obj = None
            if os.path.exists(logo_path):
                 try:
                    from reportlab.lib.utils import ImageReader
                    img = ImageReader(logo_path)
                    iw, ih = img.getSize()
                    aspect = ih / float(iw)
                    logo_w = 80
                    logo_h = logo_w * aspect
                    logo_obj = Image(logo_path, width=logo_w, height=logo_h)
                 except: pass

            if not logo_obj:
                logo_obj = Paragraph("<b>HISTORIA</b>", ParagraphStyle('LogoText', fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor("#2C3E50")))

            date_str = inv_data[0]
            inv_num_text = Paragraph(f"<b>INVOICE #{invoice_id}</b><br/>Date: {date_str}", 
                                     ParagraphStyle('InvNum', fontName='Helvetica', fontSize=11, alignment=2, leading=14))
            
            # Header Table (2 Cols: Logo, Info)
            # Total A5 width ~420. Margins 20+20=40. Usable ~380.
            # Logo Col: 190, Info Col: 190
            header_data = [[logo_obj, inv_num_text]]
            header_table = Table(header_data, colWidths=[190, 190])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (0,0), 'LEFT'),   # Logo
                ('ALIGN', (1,0), (1,0), 'RIGHT'),  # Info
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("_"*65, normal_center)) 
            elements.append(Spacer(1, 10))

            # --- 2. Information Section (2 Columns) ---
            cust_name = inv_data[1] or 'Unknown'
            cust_phone = inv_data[2] or '-'
            cust_addr = inv_data[3] or '-'
            
            store_name = inv_data[4] or 'Main Branch'
            pay_method = inv_data[5] or 'Cash'
            
            # Left: Customer, Right: Store/Payment (Swapped for English LTR flow)
            # Actually standard English invoice: Customer on Left usually.
            
            left_col_text = [
                f"<b>Customer:</b> {cust_name}",
                f"<b>Phone:</b> {cust_phone}",
                f"<b>Address:</b> {cust_addr}"
            ]
            right_col_text = [
                f"<b>Store:</b> {store_name}",
                f"<b>Payment:</b> {pay_method}"
            ]
            
            p_left = Paragraph("<br/>".join(left_col_text), ParagraphStyle('InfoLeft', fontName='Helvetica', fontSize=10, leading=14, alignment=0))
            p_right = Paragraph("<br/>".join(right_col_text), ParagraphStyle('InfoRight', fontName='Helvetica', fontSize=10, leading=14, alignment=2)) # Align right for balance
            
            # 2 Columns of ~190 each
            info_data = [[p_left, p_right]]
            info_table = Table(info_data, colWidths=[190, 190])
            info_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 5),
                ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 15))

            # --- 3. Items Grid ---
            headers = ["Item", "Color", "Size", "Qty", "Price", "Total"]
            table_data = [headers]
            
            subtotal = 0
            for item in items:
                barcode, name, color, size, qty, price, total, item_note = item
                
                # Append item_note if exists
                display_name = name
                if item_note:
                    display_name += f" {item_note}"

                row = [
                    # name[:20] + '..' if len(name)>20 else name, # Item Name (Barcode removed to save space or merge?)
                    # User requested: "Item", "Color", "Size", "Qty", "Price", "Total"
                    # I will put Item Name in first col.
                    display_name[:30] + '..' if len(display_name)>30 else display_name,
                    color or '-',
                    size or '-',
                    str(int(qty)),
                    f"{price:.2f}",
                    f"{total:.2f}"
                ]
                table_data.append(row)
                subtotal += total
                
            # Adjusted Column Widths for A5 (Total ~380)
            # [130, 45, 35, 35, 60, 75] = 380
            col_widths = [130, 45, 35, 35, 60, 75]
            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, 0), 10), 
                ('FONTSIZE', (0, 1), (-1, -1), 9), 
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 15))

            # --- 4. Totals Footer ---
            discount_amount = inv_data[7] or 0 # Correct index check? 
            # SQL: date, c.name, c.phone, c.address, s.name, i.payment_method, i.delegate_name, i.discount_percent...
            # Indices: 0, 1, 2, 3, 4, 5, 6, 7 (disc), 8 (tax), 9 (ship), 10 (notes), 11 (paid), 12 (rem), 13 (net)
            
            tax_percent = inv_data[8] or 0
            shipping_cost = inv_data[9] or 0
            
            # Discount is Fixed Amount (LE)
            discount_value = discount_amount
            after_discount = subtotal - discount_value
            tax_value = after_discount * (tax_percent / 100)
            net_total = after_discount + tax_value + shipping_cost
            # Align totals to the Left (or visual right for Arabic, but let's stack them nicely)
            
            totals_data = []
            totals_data.append(["Subtotal:", f"{subtotal:,.2f}"])
            
            # Always show Discount, Shipping, Tax
            disc_str = f"-{discount_value:,.2f}" if discount_value > 0 else "0.00"
            totals_data.append(["Discount:", disc_str])
            
            totals_data.append(["Shipping:", f"{shipping_cost:,.2f}"])
            totals_data.append(["Tax:", f"{tax_value:,.2f}"])
                
            totals_data.append(["NET TOTAL:", f"{net_total:,.2f}"])
            
            totals_table = Table(totals_data, colWidths=[100, 120])
            totals_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'), # Labels
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Values
                ('FONTSIZE', (0, 0), (-1, -2), 10),
                ('FONTSIZE', (0, -1), (-1, -1), 14), # Net Total Big
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor("#2C3E50")),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
                ('TOPPADDING', (0, -1), (-1, -1), 5),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            
            # Wrap totals table
            wrapper_table = Table([[None, totals_table]], colWidths=[160, 220])
            wrapper_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
            elements.append(wrapper_table)

            # Paid/Remaining
            elements.append(Spacer(1, 10))
            paid_amount = inv_data[11] or 0
            remaining_amount = inv_data[12] or 0
            if paid_amount > 0 or remaining_amount > 0:
                payment_info = [
                    f"Paid: {paid_amount:,.2f}",
                    f"Remaining: {remaining_amount:,.2f}"
                ]
                elements.append(Paragraph("  |  ".join(payment_info), ParagraphStyle('PayInfo', fontName='Helvetica', fontSize=11, alignment=1)))
            
            # Notes
            if inv_data[10]:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph(f"Notes: {inv_data[10]}", ParagraphStyle('Notes', fontName='Helvetica', fontSize=10, textColor=colors.grey)))
            
            # --- 5. Footer Slogan ---
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("_"*65, normal_center))
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("Thank you for shopping with HISTORIA", ParagraphStyle('Footer1', fontName='Helvetica', fontSize=10, alignment=1)))
            elements.append(Spacer(1, 15)) # Increased spacing as requested
            elements.append(Paragraph("Fashion that tells a story", ParagraphStyle('FooterEn', fontName='Helvetica-Oblique', fontSize=10, alignment=1, textColor=colors.grey)))

            doc.build(elements)
            
            # --- WhatsApp Desktop Protocol ---
            if open_whatsapp:
                phone = self.last_saved_customer_phone.replace(" ", "").replace("-", "")
                if not phone.startswith("+"):
                    phone = f"+{phone}"
                
                invoice_msg = f"Invoice #{invoice_id}"
                encoded_msg = urllib.parse.quote(invoice_msg)
                
                whatsapp_url = f"whatsapp://send?phone={phone}&text={encoded_msg}"
                webbrowser.open(whatsapp_url)
                messagebox.showinfo("Done", f"Saved to:\n{pdf_path}\n\nWhatsApp opened. Please attach file manually.")
            else:
                messagebox.showinfo("Done", f"Saved to:\n{pdf_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")
            import traceback
            traceback.print_exc()

    def load_for_edit(self, iid):
        self.editing_id = iid
        self.lbl_inv_num.configure(text=f"EDITING #{iid}", text_color="#E67E22")
        self.btn_save.configure(text="UPDATE INVOICE", fg_color="#E67E22")
        sql = """SELECT i.date, c.id, c.name, c.phone, c.address, s.name, i.channel, i.payment_method, sf.name, i.delegate_name, i.discount_percent, i.shipping_cost, i.notes, i.paid_amount FROM invoices i LEFT JOIN customers c ON i.customer_id=c.id LEFT JOIN stores s ON i.store_id=s.id LEFT JOIN safes sf ON i.safe_id=sf.id WHERE i.id=?"""
        row = self.db.fetch_one(sql, (iid,))
        if not row: return
        self.lbl_date.configure(text=row[0]); self.cust_id = row[1]
        self.ent_cust_name.delete(0, "end"); self.ent_cust_name.insert(0, row[2])
        self.phone_var.set(row[3]); self.ent_cust_addr.delete(0, "end"); self.ent_cust_addr.insert(0, row[4] or "")
        self.cb_store.set(row[5]); self.cb_channel.set(row[6]); self.cb_pay_method.set(row[7])
        self.update_safes(row[7])
        if row[8]: self.cb_safe.set(row[8])
        if row[9] in ["ARRIVE", "Others"]: self.delivery_var.set("Shipping"); self.cb_delivery_agent.set(row[9])
        else: self.delivery_var.set("Delegate"); self.cb_delivery_agent.set(row[9])
        self.toggle_delivery()
        self.ent_disc_pct.delete(0, "end"); self.ent_disc_pct.insert(0, str(row[10]))
        self.ent_shipping.delete(0, "end"); self.ent_shipping.insert(0, str(row[11]))
        self.txt_notes.delete("1.0", "end"); self.txt_notes.insert("1.0", row[12] or "")
        
        self.ent_paid.delete(0, "end"); self.ent_paid.insert(0, str(row[13] or 0))
        self.paid_manually_edited = True 
        
        for w in self.scroll_frame.winfo_children(): w.destroy()
        self.cart_items = []
        items = self.db.fetch_all("""SELECT d.barcode, i.name, c.name, s.name, id.qty, id.price, d.id, id.item_note FROM invoice_details id JOIN item_details d ON id.item_detail_id=d.id JOIN items i ON d.item_id=i.id LEFT JOIN colors c ON d.color_id=c.id LEFT JOIN sizes s ON d.size_id=s.id WHERE id.invoice_id=?""", (iid,))
        for it in items: self.add_row_populated(it)
        self.grand_total()

    def add_row_populated(self, data):
        row = ctk.CTkFrame(self.scroll_frame, height=35, fg_color="transparent")
        row.pack(fill="x", pady=2); row.pack_propagate(False)
        entries = {}
        def mk(key, w, state="normal", val=""):
            e = ctk.CTkEntry(row, width=w, height=28, state=state, font=("Arial", 12))
            if key in ["qty", "price"]: e.configure(validate="key", validatecommand=self.vcmd)
            e.pack(side="left", padx=2)
            e.insert(0, str(val))
            if state=="readonly": e.configure(state="readonly")
            entries[key] = e
            return e
        d = {"frame": row, "id": data[6]}
        
        barcode_frame = ctk.CTkFrame(row, fg_color="transparent", width=COLS["barcode"])
        barcode_frame.pack(side="left", padx=2); barcode_frame.pack_propagate(False)
        d["barcode"] = ctk.CTkEntry(barcode_frame, width=COLS["barcode"]-35, height=28, font=("Arial", 12))
        d["barcode"].insert(0, str(data[0]))
        d["barcode"].pack(side="left", padx=2)
        ctk.CTkButton(barcode_frame, text="🔍", width=30, height=28, fg_color="#3498DB", command=lambda: self.open_search_popup(d), font=("Arial", 12)).pack(side="left", padx=2)
        
        d["name"] = mk("name", COLS["name"], "readonly", data[1])
        d["color"] = mk("color", COLS["color"], "readonly", data[2] or "-")
        d["size"] = mk("size", COLS["size"], "readonly", data[3] or "-")
        
        # --- Display Design as Plain for Edit Mode (Safe Fallback) ---
        d["design"] = ctk.CTkComboBox(row, values=["Plain / سادة"], width=120, font=("Arial", 12), state="disabled")
        # If item_note exists, try to set the design combobox to that value, otherwise "Plain / سادة"
        item_note_val = data[7] # item_note is the 8th element in the data tuple (index 7)
        if item_note_val and item_note_val.startswith(" [") and item_note_val.endswith("]"):
            design_name_from_note = item_note_val[2:-1]
            # Reconstruct the combobox value if possible, e.g., "Name (+Price)"
            # This is tricky without the price. For now, just display the name.
            # Or, better, just set it to "Plain / سادة" and disable it, as changing design in edit mode is complex.
            # The price is already loaded correctly.
            d["design"].set(design_name_from_note) # Display the name from the note
        else:
            d["design"].set("Plain / سادة")
        d["design"].pack(side="left", padx=2)
        
        d["qty"] = mk("qty", COLS["qty"], "normal", data[4])
        d["price"] = mk("price", COLS["price"], "normal", data[5])
        
        # Don't set base_price here because we don't know if design is included.
        # Changing Design in Edit Mode is disabled for safety.
        d["base_price"] = data[5] 
        
        lbl = ctk.CTkLabel(row, text=f"{data[4]*data[5]:.2f}", width=COLS["total"], font=("Arial", 12))
        lbl.pack(side="left", padx=2)
        d["total_lbl"] = lbl
        ctk.CTkButton(row, text="X", width=30, height=25, fg_color="#C0392B", command=lambda: self.del_row(d), font=("Arial", 10)).pack(side="left", padx=2)
        self.cart_items.append(d)
        d["barcode"].bind("<Return>", lambda x: self.lookup(d))
        d["qty"].bind("<KeyRelease>", lambda x: self.calc_row(d))
        d["price"].bind("<KeyRelease>", lambda x: self.calc_row(d))

    def load_data(self):
        stores = self.db.fetch_all("SELECT name FROM stores")
        if stores: 
            self.cb_store.configure(values=[s[0] for s in stores])
            self.cb_store.set(stores[0][0])
        chans = self.db.fetch_all("SELECT DISTINCT channel FROM invoices WHERE channel IS NOT NULL AND channel != ''")
        vals_c = [c[0] for c in chans]
        if not vals_c: vals_c = ["Store", "Online", "Instagram"]
        self.cb_channel.configure(values=vals_c)
        self.update_safes("Cash")
        self.toggle_delivery()
        self.load_hd_data()

    def load_hd_data(self):
        # Fetch HD items with Barcode
        hd_items = self.db.fetch_all("SELECT d.id, i.name, d.sell_price, d.barcode FROM item_details d JOIN items i ON d.item_id=i.id WHERE d.barcode LIKE 'HD%'")
        self.hd_map = {}
        self.hd_barcode_lookup = {}
        
        for iid, n, p, bar in hd_items:
            # Format: "HD212 - Eagle (+50)"
            display_str = f"{bar} - {n} (+{p})"
            self.hd_map[display_str] = {"id": iid, "price": p, "name": n}
            self.hd_barcode_lookup[bar.upper()] = display_str

        self.hd_options = ["Plain / سادة"] + list(self.hd_map.keys())

    def toggle_delivery(self):
        if self.delivery_var.get() == "Delegate":
            users = self.db.fetch_all("SELECT DISTINCT delegate_name FROM invoices WHERE delegate_name IS NOT NULL AND delegate_name != '' AND delegate_name NOT IN ('ARRIVE','Others')")
            vals = [u[0] for u in users]
            if not vals: vals = ["Admin"]
            self.cb_delivery_agent.configure(values=vals)
            if vals: self.cb_delivery_agent.set(vals[0])
        else:
            self.cb_delivery_agent.configure(values=["ARRIVE", "Others"]); self.cb_delivery_agent.set("ARRIVE")

    def validate_phone(self, *args):
        val = self.phone_var.get()
        clean = "".join([c for c in val if c.isdigit() or c == "+"])
        if not clean.startswith("+20"): self.phone_var.set("+20")
        elif len(clean) > 13: self.phone_var.set(clean[:13])
        elif val != clean: self.phone_var.set(clean)

    def update_safes(self, choice):
        val = choice if isinstance(choice, str) else self.cb_pay_method.get()
        all_safes = [s[0] for s in self.db.fetch_all("SELECT name FROM safes")]
        filtered = [s for s in all_safes if "Bank" in s] if val == "Visa" else [s for s in all_safes if "Bank" not in s]
        self.cb_safe.configure(values=filtered if filtered else all_safes)
        if filtered: self.cb_safe.set(filtered[0])

    def search_customer(self, e=None):
        name = self.ent_cust_name.get().strip()
        phone = self.ent_cust_phone.get().strip()
        res = None
        if len(phone) > 4: res = self.db.fetch_one("SELECT id, name, phone, address FROM customers WHERE phone=?", (phone,))
        if not res and name: res = self.db.fetch_one("SELECT id, name, phone, address FROM customers WHERE name LIKE ?", (f"%{name}%",))
        if res:
            self.cust_id = res[0]
            self.ent_cust_name.delete(0, "end")
            self.ent_cust_name.insert(0, res[1])
            if self.focus_get() != self.ent_cust_phone: self.phone_var.set(res[2] or "+20")
            self.ent_cust_addr.delete(0, "end")
            self.ent_cust_addr.insert(0, res[3] or "")
            if self.cart_items: self.cart_items[0]['barcode'].focus()
        else: self.cust_id = None

    def add_row(self, e=None):
        row = ctk.CTkFrame(self.scroll_frame, height=35, fg_color="transparent")
        row.pack(fill="x", pady=2); row.pack_propagate(False)
        entries = {}
        def mk(key, w, state="normal", ph=""):
            e = ctk.CTkEntry(row, width=w, height=28, state=state, placeholder_text=ph, font=("Arial", 12))
            e.pack(side="left", padx=2)
            entries[key] = e
            return e
        d = {"frame": row, "id": None}
        
        barcode_frame = ctk.CTkFrame(row, fg_color="transparent", width=COLS["barcode"])
        barcode_frame.pack(side="left", padx=2); barcode_frame.pack_propagate(False)
        d["barcode"] = ctk.CTkEntry(barcode_frame, width=COLS["barcode"]-35, height=28, placeholder_text="Scan", font=("Arial", 12))
        d["barcode"].pack(side="left", padx=2)
        ctk.CTkButton(barcode_frame, text="🔍", width=30, height=28, fg_color="#3498DB", command=lambda: self.open_search_popup(d), font=("Arial", 12)).pack(side="left", padx=2)
        
        d["name"] = mk("name", COLS["name"], "readonly")
        d["color"] = mk("color", COLS["color"], "readonly")
        d["size"] = mk("size", COLS["size"], "readonly")
        
        # --- HD Design Combobox ---
        # Data pre-loaded in load_hd_data()
        options = getattr(self, "hd_options", ["Plain / سادة"])
        
        d["design"] = ctk.CTkComboBox(row, values=options, width=120, font=("Arial", 12), dropdown_font=("Arial", 12), command=lambda val: self.on_design_change(d, val))
        d["design"].pack(side="left", padx=2)
        d["design"].set("Plain / سادة")
        
        # Gallery Button
        ctk.CTkButton(row, text="🖼️", width=30, height=28, fg_color="#E74C3C", command=lambda: self.open_design_gallery(d), font=("Arial", 12)).pack(side="left", padx=2)

        # Bind FocusOut or Return to handle typed barcodes
        d["design"].bind("<Return>", lambda e: self.on_design_change(d, d["design"].get()))
        d["design"].bind("<FocusOut>", lambda e: self.on_design_change(d, d["design"].get()))

        d["qty"] = mk("qty", COLS["qty"])
        d["qty"].configure(validate="key", validatecommand=self.vcmd)
        d["qty"].insert(0, "1")
        
        d["price"] = mk("price", COLS["price"]) # This will hold Base + Design Price
        d["price"].configure(validate="key", validatecommand=self.vcmd)
        
        # Hidden field to store Base Price of the sweater/hoodie to revert changes
        d["base_price"] = 0.0 
        
        lbl = ctk.CTkLabel(row, text="0.00", width=COLS["total"], font=("Arial", 12))
        lbl.pack(side="left", padx=2)
        d["total_lbl"] = lbl
        ctk.CTkButton(row, text="X", width=30, height=25, fg_color="#C0392B", command=lambda: self.del_row(d), font=("Arial", 10)).pack(side="left", padx=2)
        self.cart_items.append(d)
        d["barcode"].bind("<Return>", lambda x: self.lookup(d))
        d["qty"].bind("<KeyRelease>", lambda x: self.calc_row(d))
        d["price"].bind("<KeyRelease>", lambda x: self.calc_row(d))
        d["barcode"].focus()

    def on_design_change(self, d, val):
        # Handle Typed Barcodes
        val = val.strip()
        final_val = val
        
        # If user typed "HD...", check lookup
        if val.upper() in self.hd_barcode_lookup:
            final_val = self.hd_barcode_lookup[val.upper()]
            # Auto-update the combobox text to full format
            try: d["design"].set(final_val)
            except: pass
        
        # Update Price based on Design
        try:
            base_p = float(d["base_price"])
            design_cost = 0.0
            if final_val != "Plain / سادة" and final_val in self.hd_map:
                design_cost = self.hd_map[final_val]["price"]
            
            new_price = base_p + design_cost
            d["price"].configure(state="normal")
            d["price"].delete(0, "end")
            d["price"].insert(0, str(new_price))
            
            self.calc_row(d)
        except: pass

    def open_design_gallery(self, d):
        def on_select(barcode):
            # Formatted key for lookup (needs helper to find fast, or just iterate map)
            # The gallery returns Barcode (e.g. HD212).
            # Order page expects the Full String Key "HD212 - Name (+Price)" OR handles Barcode in on_design_change
            # Our on_design_change ALREADY handles raw barcodes!
            
            # So we set the raw barcode and trigger on_design_change
            d["design"].set(barcode)
            self.on_design_change(d, barcode)

        popup = DesignGalleryPopup(self, self.db, on_select)

    def lookup(self, d):
        code = d['barcode'].get().strip().upper() 
        d['barcode'].configure(state="normal")
        d['barcode'].delete(0, "end")
        d['barcode'].insert(0, code)
        
        store = self.cb_store.get()
        sql = """SELECT d.id, i.name, c.name, s.name, d.sell_price FROM item_details d JOIN items i ON d.item_id=i.id LEFT JOIN colors c ON d.color_id=c.id LEFT JOIN sizes s ON d.size_id=s.id WHERE d.barcode=?"""
        res = self.db.fetch_one(sql, (code,))
        if res:
            d['id'] = res[0]
            for k, v in zip(["name", "color", "size"], [res[1], res[2], res[3]]):
                d[k].configure(state="normal"); d[k].delete(0, "end"); d[k].insert(0, str(v or "-")); d[k].configure(state="readonly")
            
            base_sell = float(res[4])
            d['base_price'] = base_sell
            
            # Apply existing design markup if selected
            design_cost = 0.0
            curr_design = d["design"].get()
            if curr_design != "Plain / سادة" and hasattr(self, 'hd_map') and curr_design in self.hd_map:
                design_cost = self.hd_map[curr_design]["price"]
            
            total_sell = base_sell + design_cost
            
            d['price'].delete(0, "end"); d['price'].insert(0, str(total_sell))
            self.calc_row(d); d['qty'].focus()
        else: 
            d['barcode'].configure(text_color="red")
            
    def calc_row(self, d):
        try:
            q = float(d['qty'].get()); p = float(d['price'].get())
            d['total_lbl'].configure(text=f"{q*p:.2f}")
            self.grand_total()
        except: pass

    def del_row(self, d):
        d['frame'].destroy()
        self.cart_items.remove(d)
        self.grand_total()

    def reset_form(self):
        self.editing_id = None
        self.lbl_inv_num.configure(text="New (Auto)", text_color="#2CC985")
        self.btn_save.configure(text="SAVE (F5)", fg_color="#2CC985")
        
        self.ent_cust_name.delete(0, "end")
        self.ent_cust_phone.delete(0, "end"); self.phone_var.set("+20")
        self.ent_cust_addr.delete(0, "end")
        self.ent_paid.delete(0, "end"); self.ent_paid.insert(0, "0")
        self.ent_disc_pct.delete(0, "end"); self.ent_disc_pct.insert(0, "0")
        self.ent_shipping.delete(0, "end"); self.ent_shipping.insert(0, "0")
        self.txt_notes.delete("1.0", "end")
        self.cust_id = None
        self.paid_manually_edited = False
        
        for item in self.cart_items:
            item['frame'].destroy()
        self.cart_items = []
        self.add_row()
        self.grand_total()
