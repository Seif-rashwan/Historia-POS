
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from datetime import date
import os
from app.database import DB
from app.utils import fix_text, REPORTLAB_AVAILABLE

# Conditional imports for ReportLab
if REPORTLAB_AVAILABLE:
    from app.utils import (
        SimpleDocTemplate, A4, Table, TableStyle, Paragraph, Spacer, 
        colors, getSampleStyleSheet, ParagraphStyle, pdfmetrics, TTFont
    )

class ReportsPage(ctk.CTkFrame):
    def __init__(self, parent, user_role="Admin"):
        super().__init__(parent)
        self.user_role = user_role
        self.db = DB()
        
        # Fonts
        self.AR_FONT = ("Segoe UI", 12)
        self.AR_FONT_BOLD = ("Segoe UI", 13, "bold")
        self.AR_FONT_HEADER = ("Segoe UI", 20, "bold")
        
        # --- Header ---
        header = ctk.CTkFrame(self, height=60)
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text=fix_text("التقارير والتحليلات"), 
                     font=self.AR_FONT_HEADER, text_color="#8E44AD").pack(side="right", padx=20)

        # --- Filters Bar ---
        filters = ctk.CTkFrame(self)
        filters.pack(fill="x", padx=10, pady=5)
        
        # Report Type
        ctk.CTkLabel(filters, text=fix_text(":نوع التقرير"), font=self.AR_FONT).pack(side="right", padx=5)
        report_values = [
            fix_text("تقرير المبيعات"), 
            fix_text("تقرير جرد المخزون"),
            fix_text("تقرير جرد تفصيلي (Grouping)"),
            fix_text("تقرير النواقص (Low Stock)"),
            fix_text("تقرير العملاء"),
            fix_text("تقرير الفواتير الآجلة"),
            fix_text("تقرير الأصناف الأكثر مبيعاً"),
            fix_text("تقرير المبيعات اليومية"),
            fix_text("تقرير مرتجع المبيعات"),
            fix_text("تقرير المخزون الراكد (Dead Stock)"),
            fix_text("تقرير أداء المندوبين"),
            fix_text("كشف حساب عميل")
        ]
        # Add Admin-only reports
        if self.user_role == "Admin":
            report_values.insert(3, fix_text("تقرير الأرباح (تقريبي)"))
            report_values.insert(5, fix_text("تقرير الموردين"))
            report_values.insert(7, fix_text("تقرير حركة الخزنة (Cash Flow)"))
            report_values.insert(8, fix_text("تقرير صافي الربح (Net Profit)"))
        
        self.cb_report = ctk.CTkComboBox(filters, width=200, font=self.AR_FONT, justify="right",
                                         values=report_values, command=self.toggle_filters)
        self.cb_report.pack(side="right", padx=5)
        self.cb_report.set(fix_text("تقرير المبيعات"))
        
        # Date Filters (Default - shown for most reports)
        self.date_frame = ctk.CTkFrame(filters, fg_color="transparent")
        self.date_frame.pack(side="right", padx=10)
        
        ctk.CTkLabel(self.date_frame, text=fix_text(":إلى"), font=self.AR_FONT).pack(side="right", padx=2)
        self.ent_date_to = ctk.CTkEntry(self.date_frame, width=100, font=("Arial", 12))
        self.ent_date_to.pack(side="right", padx=2)
        self.ent_date_to.insert(0, str(date.today()))
        
        ctk.CTkLabel(self.date_frame, text=fix_text(":من"), font=self.AR_FONT).pack(side="right", padx=2)
        self.ent_date_from = ctk.CTkEntry(self.date_frame, width=100, font=("Arial", 12))
        self.ent_date_from.pack(side="right", padx=2)
        # Default to first of month
        first_of_month = date.today().replace(day=1)
        self.ent_date_from.insert(0, str(first_of_month))
        
        # Store Filter (Optional)
        self.store_label = ctk.CTkLabel(filters, text=fix_text(":المخزن"), font=self.AR_FONT)
        self.store_label.pack(side="right", padx=5)
        self.cb_store = ctk.CTkComboBox(filters, width=150, font=self.AR_FONT, justify="right")
        self.cb_store.pack(side="right", padx=5)
        
        # HD Filter Checkbox (Global)
        self.cb_include_hd = ctk.CTkCheckBox(filters, text=fix_text("تضمين التصميمات (HD)"), 
                                              font=self.AR_FONT)
        self.cb_include_hd.pack(side="right", padx=5)
        self.cb_include_hd.select()  # Checked by default (include HD)
        
        # Safe Filter (for Cash Flow)
        self.safe_label = ctk.CTkLabel(filters, text=fix_text(":الخزينة"), font=self.AR_FONT)
        self.safe_label.pack_forget()  # Hidden by default
        self.cb_safe = ctk.CTkComboBox(filters, width=150, font=self.AR_FONT, justify="right")
        self.cb_safe.pack_forget()  # Hidden by default
        
        # Dead Stock - Days Entry (Hidden by default)
        self.days_label = ctk.CTkLabel(filters, text=fix_text(":أيام عدم البيع"), font=self.AR_FONT)
        self.days_label.pack_forget()
        self.ent_days = ctk.CTkEntry(filters, width=80, font=("Arial", 12))
        self.ent_days.pack_forget()
        self.ent_days.insert(0, "30")
        
        # Customer Statement - Customer Name Entry (Hidden by default)
        self.customer_label = ctk.CTkLabel(filters, text=fix_text(":اسم العميل"), font=self.AR_FONT)
        self.customer_label.pack_forget()
        self.cb_customer = ctk.CTkComboBox(filters, width=200, font=self.AR_FONT, justify="right")
        self.cb_customer.pack_forget()
        
        # Search Button
        ctk.CTkButton(filters, text=fix_text("عرض التقرير"), command=self.generate_report, 
                      font=self.AR_FONT_BOLD, width=120, fg_color="#3498DB").pack(side="right", padx=20)

        # --- Results Table ---
        self.tree = ttk.Treeview(self, show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- Footer (Exports) ---
        footer = ctk.CTkFrame(self, height=60)
        footer.pack(fill="x", padx=10, pady=10)
        
        # ENGLISH BUTTONS
        ctk.CTkButton(footer, text="Export Excel 📗", command=self.export_excel, 
                      fg_color="#27AE60", font=("Arial", 12, "bold"), height=40).pack(side="left", padx=10)
                      
        ctk.CTkButton(footer, text="Export PDF 📕", command=self.export_pdf, 
                      fg_color="#C0392B", font=("Arial", 12, "bold"), height=40).pack(side="left", padx=10)
        
        self.lbl_total = ctk.CTkLabel(footer, text="", font=("Segoe UI", 16, "bold"), text_color="#F39C12")
        self.lbl_total.pack(side="right", padx=20)
        
        self.load_stores()
        self.current_data = [] # To store raw data for export
        self.current_columns = []
        self.current_report_type = ""

    def load_stores(self):
        stores = [s[0] for s in self.db.fetch_all("SELECT name FROM stores")]
        stores.insert(0, fix_text("كل المخازن"))
        self.cb_store.configure(values=stores)
        self.cb_store.set(stores[0])

    def toggle_filters(self, choice):
        # Hide all dynamic filters first
        self.safe_label.pack_forget()
        self.cb_safe.pack_forget()
        self.store_label.pack_forget()
        self.cb_store.pack_forget()
        self.date_frame.pack_forget()
        self.days_label.pack_forget()
        self.ent_days.pack_forget()
        self.customer_label.pack_forget()
        self.cb_customer.pack_forget()
        
        # Show appropriate filters based on report type
        if choice == fix_text("تقرير حركة الخزنة (Cash Flow)"):
            self.date_frame.pack(side="right", padx=10, after=self.cb_report)
            self.safe_label.pack(side="right", padx=5, after=self.date_frame)
            self.cb_safe.pack(side="right", padx=5, after=self.safe_label)
            self.load_safes()
        
        elif choice == fix_text("تقرير المخزون الراكد (Dead Stock)"):
            self.store_label.pack(side="right", padx=5, after=self.cb_report)
            self.cb_store.pack(side="right", padx=5, after=self.store_label)
            self.days_label.pack(side="right", padx=5, after=self.cb_store)
            self.ent_days.pack(side="right", padx=5, after=self.days_label)
        
        elif choice == fix_text("كشف حساب عميل"):
            self.customer_label.pack(side="right", padx=5, after=self.cb_report)
            self.cb_customer.pack(side="right", padx=5, after=self.customer_label)
            custs = self.db.fetch_all("SELECT name FROM customers ORDER BY name")
            vals = [c[0] for c in custs]
            self.cb_customer.configure(values=vals)
            if vals: self.cb_customer.set(vals[0])
            self.date_frame.pack(side="right", padx=10, after=self.cb_customer)
        
        elif choice == fix_text("تقرير جرد المخزون") or choice == fix_text("تقرير النواقص (Low Stock)") or choice == fix_text("تقرير جرد تفصيلي (Grouping)"):
            self.store_label.pack(side="right", padx=5, after=self.cb_report)
            self.cb_store.pack(side="right", padx=5, after=self.store_label)
        
        else:
            self.store_label.pack(side="right", padx=5, after=self.cb_report)
            self.cb_store.pack(side="right", padx=5, after=self.store_label)
            self.date_frame.pack(side="right", padx=10, after=self.cb_store)
    
    def load_safes(self):
        safes = [s[0] for s in self.db.fetch_all("SELECT name FROM safes")]
        safes.insert(0, fix_text("كل الخزائن"))
        self.cb_safe.configure(values=safes)
        self.cb_safe.set(safes[0])
    
    def get_hd_filter_sql(self, table_alias="d"):
        include_hd = self.cb_include_hd.get()
        if include_hd: return ""
        else: return f" AND {table_alias}.barcode NOT LIKE 'HD%'"

    def generate_report(self):
        # Clear Tree
        self.tree.delete(*self.tree.get_children())
        self.current_data = []
        
        report_type = self.cb_report.get()
        self.current_report_type = report_type
        d_from = self.ent_date_from.get()
        d_to = self.ent_date_to.get()
        store = self.cb_store.get()
        
        # 1. SALES REPORT
        if report_type == fix_text("تقرير المبيعات"):
            self.current_columns = ["ID", "Date", "Customer", "Items", "Total", "Paid", "Remaining", "User"]
            cols_ar = ["رقم الفاتورة", "التاريخ", "العميل", "عدد الأصناف", "الإجمالي", "المدفوع", "المتبقي", "المندوب"]
            
            include_hd = self.cb_include_hd.get()
            if not include_hd:
                sql = """SELECT i.id, i.date, c.name, 
                        COUNT(DISTINCT CASE WHEN d.barcode NOT LIKE 'HD%' THEN id.id END), 
                        i.net_total, i.paid_amount, i.remaining_amount, i.delegate_name 
                        FROM invoices i 
                        LEFT JOIN customers c ON i.customer_id = c.id 
                        LEFT JOIN invoice_details id ON i.id = id.invoice_id
                        LEFT JOIN item_details d ON id.item_detail_id = d.id
                        LEFT JOIN stores s ON i.store_id = s.id 
                        WHERE i.date BETWEEN ? AND ?"""
            else:
                sql = """SELECT i.id, i.date, c.name, COUNT(DISTINCT id.id), i.net_total, i.paid_amount, i.remaining_amount, i.delegate_name 
                         FROM invoices i 
                         LEFT JOIN customers c ON i.customer_id = c.id 
                         LEFT JOIN invoice_details id ON i.id = id.invoice_id 
                         LEFT JOIN stores s ON i.store_id = s.id 
                         WHERE i.date BETWEEN ? AND ?"""
            params = [d_from, d_to]
            
            if store != fix_text("كل المخازن"):
                sql += " AND s.name = ?"
                params.append(store)
            
            sql += " GROUP BY i.id ORDER BY i.date DESC"
            data = self.db.fetch_all(sql, tuple(params))
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=100, anchor="center")
            
            total_sales = 0
            for row in data:
                display_row = list(row)
                if row[2]: display_row[2] = fix_text(row[2])
                if row[7]: display_row[7] = fix_text(row[7])
                self.tree.insert("", "end", values=display_row)
                self.current_data.append(display_row)
                total_sales += row[4]
            
            self.lbl_total.configure(text=fix_text(f"إجمالي المبيعات: {total_sales:,.2f} ج.م"))

        # 2. STOCK REPORT
        elif report_type == fix_text("تقرير جرد المخزون"):
            self.current_columns = ["Barcode", "Name", "Color", "Size", "Store", "Qty", "Cost", "Value"]
            cols_ar = ["الباركود", "الصنف", "اللون", "المقاس", "المخزن", "الكمية", "التكلفة", "قيمة المخزون"]
            
            sql = """SELECT d.barcode, i.name, IFNULL(c.name,'-'), IFNULL(siz.name,'-'), s.name, ss.quantity, d.buy_price, (ss.quantity * d.buy_price)
                     FROM store_stock ss
                     JOIN item_details d ON ss.item_detail_id = d.id
                     JOIN items i ON d.item_id = i.id
                     JOIN stores s ON ss.store_id = s.id
                     LEFT JOIN colors c ON d.color_id = c.id
                     LEFT JOIN sizes siz ON d.size_id = siz.id
                     WHERE ss.quantity != 0"""
            params = []
            
            hd_filter = self.get_hd_filter_sql("d")
            sql += hd_filter
            
            if store != fix_text("كل المخازن"):
                sql += " AND s.name = ?"
                params.append(store)
                
            sql += " ORDER BY i.name"
            data = self.db.fetch_all(sql, tuple(params))
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=100, anchor="center")
            self.tree.column("Name", width=200)
            
            total_val = 0
            for row in data:
                display_row = list(row)
                display_row[1] = fix_text(display_row[1]) # Name
                display_row[2] = fix_text(display_row[2]) # Color
                display_row[3] = fix_text(display_row[3]) # Size
                display_row[4] = fix_text(display_row[4]) # Store Name
                
                self.tree.insert("", "end", values=display_row)
                self.current_data.append(display_row)
                total_val += row[7] if row[7] else 0
                
            self.lbl_total.configure(text=fix_text(f"قيمة المخزون: {total_val:,.2f} ج.م"))

        # 3. LOW STOCK
        elif report_type == fix_text("تقرير النواقص (Low Stock)"):
            self.current_columns = ["Barcode", "Name", "Store", "Qty"]
            cols_ar = ["الباركود", "الصنف", "المخزن", "الكمية الحالية"]
            
            sql = """SELECT d.barcode, i.name, s.name, ss.quantity
                     FROM store_stock ss
                     JOIN item_details d ON ss.item_detail_id = d.id
                     JOIN items i ON d.item_id = i.id
                     JOIN stores s ON ss.store_id = s.id
                     WHERE ss.quantity <= 5 AND ss.quantity > 0"""
            
            hd_filter = self.get_hd_filter_sql("d")
            sql += hd_filter
            
            params = []
            if store != fix_text("كل المخازن"):
                sql += " AND s.name = ?"
                params.append(store)
            
            data = self.db.fetch_all(sql, tuple(params))
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=150, anchor="center")
            
            for row in data:
                d_row = list(row)
                d_row[1] = fix_text(d_row[1])
                d_row[2] = fix_text(d_row[2])
                self.tree.insert("", "end", values=d_row)
                self.current_data.append(d_row)
                
            self.lbl_total.configure(text=fix_text(f"عدد النواقص: {len(data)} صنف"))
        
        # 4. PROFIT REPORT (Approx) - FIXED: Uses historical cost_at_sale
        elif report_type == fix_text("تقرير الأرباح (تقريبي)"):
            self.current_columns = ["Item", "Sold_Qty", "Cost_at_Sale", "Sell_Price", "Profit"]
            cols_ar = ["الصنف", "الكمية المباعة", "تكلفة البيع", "سعر البيع", "الربح"]
            
            sql = """SELECT i.name, SUM(id.qty), AVG(id.cost_at_sale), AVG(id.price), SUM((id.price - id.cost_at_sale) * id.qty)
                     FROM invoice_details id
                     JOIN item_details d ON id.item_detail_id = d.id
                     JOIN items i ON d.item_id = i.id
                     JOIN invoices inv ON id.invoice_id = inv.id
                     WHERE inv.date BETWEEN ? AND ?"""
            params = [d_from, d_to]
            
            hd_filter = self.get_hd_filter_sql("d")
            sql += hd_filter
            
            if store != fix_text("كل المخازن"):
                sql += " AND inv.store_id = (SELECT id FROM stores WHERE name = ?)"
                params.append(store)
            
            sql += " GROUP BY i.id ORDER BY SUM((id.price - id.cost_at_sale) * id.qty) DESC"
            data = self.db.fetch_all(sql, tuple(params))
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=120, anchor="center")
            
            total_profit = 0
            for row in data:
                d_row = list(row)
                d_row[0] = fix_text(d_row[0])
                profit = d_row[4] if d_row[4] else 0
                total_profit += profit
                self.tree.insert("", "end", values=d_row)
                self.current_data.append(d_row)
            
            self.lbl_total.configure(text=fix_text(f"إجمالي الأرباح: {total_profit:,.2f} ج.م"))
        
        # 5. CUSTOMERS REPORT
        elif report_type == fix_text("تقرير العملاء"):
            self.current_columns = ["ID", "Name", "Phone", "Total_Invoices", "Total_Spent", "Remaining"]
            cols_ar = ["رقم العميل", "الاسم", "الهاتف", "عدد الفواتير", "إجمالي المشتريات", "المتبقي"]
            
            sql = """SELECT c.id, c.name, c.phone, COUNT(i.id), SUM(i.net_total), SUM(i.remaining_amount)
                     FROM customers c
                     LEFT JOIN invoices i ON c.id = i.customer_id
                     WHERE (i.date BETWEEN ? AND ? OR i.date IS NULL)"""
            params = [d_from, d_to]
            
            sql += " GROUP BY c.id ORDER BY SUM(i.net_total) DESC"
            data = self.db.fetch_all(sql, tuple(params))
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=120, anchor="center")
            
            for row in data:
                d_row = list(row)
                if d_row[1]: d_row[1] = fix_text(d_row[1])
                self.tree.insert("", "end", values=d_row)
                self.current_data.append(d_row)
            
            self.lbl_total.configure(text=fix_text(f"عدد العملاء: {len(data)}"))
        
        # 6. SUPPLIERS REPORT
        elif report_type == fix_text("تقرير الموردين"):
            self.current_columns = ["ID", "Name", "Phone", "Total_Purchases", "Total_Spent"]
            cols_ar = ["رقم المورد", "الاسم", "الهاتف", "عدد المشتريات", "إجمالي المشتريات"]
            
            sql = """SELECT s.id, s.name, s.phone, COUNT(p.id), SUM(p.net_total)
                     FROM suppliers s
                     LEFT JOIN purchases p ON s.id = p.supplier_id
                     WHERE (p.date BETWEEN ? AND ? OR p.date IS NULL)"""
            params = [d_from, d_to]
            
            sql += " GROUP BY s.id ORDER BY SUM(p.net_total) DESC"
            data = self.db.fetch_all(sql, tuple(params))
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=120, anchor="center")
            
            for row in data:
                d_row = list(row)
                if d_row[1]: d_row[1] = fix_text(d_row[1])
                self.tree.insert("", "end", values=d_row)
                self.current_data.append(d_row)
            
            self.lbl_total.configure(text=fix_text(f"عدد الموردين: {len(data)}"))
        
        # 7. PENDING INVOICES REPORT
        elif report_type == fix_text("تقرير الفواتير الآجلة"):
            self.current_columns = ["ID", "Date", "Customer", "Total", "Paid", "Remaining"]
            cols_ar = ["رقم الفاتورة", "التاريخ", "العميل", "الإجمالي", "المدفوع", "المتبقي"]
            
            sql = """SELECT i.id, i.date, c.name, i.net_total, i.paid_amount, i.remaining_amount
                     FROM invoices i
                     LEFT JOIN customers c ON i.customer_id = c.id
                     WHERE i.remaining_amount > 0.01"""
            
            if store != fix_text("كل المخازن"):
                sql += " AND i.store_id = (SELECT id FROM stores WHERE name = ?)"
                data = self.db.fetch_all(sql, (store,))
            else:
                data = self.db.fetch_all(sql)
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=120, anchor="center")
            
            total_remaining = 0
            for row in data:
                d_row = list(row)
                if d_row[2]: d_row[2] = fix_text(d_row[2])
                self.tree.insert("", "end", values=d_row)
                self.current_data.append(d_row)
                total_remaining += row[5] if row[5] else 0
            
            self.lbl_total.configure(text=fix_text(f"إجمالي المتبقي: {total_remaining:,.2f} ج.م"))
        
        # 8. CASH FLOW REPORT
        elif report_type == fix_text("تقرير حركة الخزنة (Cash Flow)"):
            self.current_columns = ["Type", "Date", "Description", "Amount", "Balance"]
            cols_ar = ["النوع", "التاريخ", "الوصف", "المبلغ", "الرصيد"]
            
            safe = self.cb_safe.get()
            safe_id = None
            if safe != fix_text("كل الخزائن"):
                safe_res = self.db.fetch_one("SELECT id FROM safes WHERE name=?", (safe,))
                if safe_res: safe_id = safe_res[0]
            
            movements = []
            
            # Invoices
            sql_invoices = """SELECT 'مبيعات', i.date, ('فاتورة #' || i.id || ' - ' || COALESCE(c.name, 'غير معروف')), i.paid_amount, NULL
                              FROM invoices i
                              LEFT JOIN customers c ON i.customer_id = c.id
                              WHERE i.date BETWEEN ? AND ?"""
            params_inv = [d_from, d_to]
            if safe_id:
                sql_invoices += " AND i.safe_id = ?"
                params_inv.append(safe_id)
            else:
                sql_invoices += " AND i.safe_id IS NOT NULL"
            
            movements.extend(self.db.fetch_all(sql_invoices, tuple(params_inv)))
            
            # Receipts
            sql_receipts = """SELECT 'سند قبض', date, description, amount, NULL
                              FROM vouchers
                              WHERE voucher_type = 'Receipt' AND date BETWEEN ? AND ?"""
            params_rec = [d_from, d_to]
            if safe_id:
                sql_receipts += " AND safe_id = ?"
                params_rec.append(safe_id)
            movements.extend(self.db.fetch_all(sql_receipts, tuple(params_rec)))
            
            # Purchases
            sql_purchases = """SELECT 'مشتريات', p.date, ('فاتورة شراء #' || p.id || ' - ' || COALESCE(s.name, 'غير معروف')), -p.net_total, NULL
                               FROM purchases p
                               LEFT JOIN suppliers s ON p.supplier_id = s.id
                               WHERE p.payment_method != 'أجل' AND p.date BETWEEN ? AND ?"""
            params_pur = [d_from, d_to]
            if safe_id:
                sql_purchases += " AND p.safe_id = ?"
                params_pur.append(safe_id)
            else:
                sql_purchases += " AND p.safe_id IS NOT NULL"
            
            movements.extend(self.db.fetch_all(sql_purchases, tuple(params_pur)))
            
            # Payments
            sql_payments = """SELECT 'سند صرف', date, description, -amount, NULL
                              FROM vouchers
                              WHERE voucher_type = 'Payment' AND date BETWEEN ? AND ?"""
            params_pay = [d_from, d_to]
            if safe_id:
                sql_payments += " AND safe_id = ?"
                params_pay.append(safe_id)
            movements.extend(self.db.fetch_all(sql_payments, tuple(params_pay)))
            
            # Returns
            sql_returns = """SELECT 'مرتجع مبيعات', r.date, ('مرتجع فاتورة #' || r.invoice_id), -r.refund_amount, NULL
                             FROM returns r
                             JOIN invoices i ON r.invoice_id = i.id
                             WHERE r.date BETWEEN ? AND ?"""
            params_ret = [d_from, d_to]
            if safe_id:
                sql_returns += " AND i.safe_id = ?"
                params_ret.append(safe_id)
            movements.extend(self.db.fetch_all(sql_returns, tuple(params_ret)))
            
            movements.sort(key=lambda x: x[1] if x[1] else "")
            
            balance = 0.0
            data_with_balance = []
            for mov in movements:
                amount = mov[3] if mov[3] else 0
                balance += amount
                row = list(mov)
                row[4] = balance 
                data_with_balance.append(row)
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=120, anchor="center")
            self.tree.column("Description", width=250)
            
            total_in = sum(m[3] for m in movements if m[3] and m[3] > 0)
            total_out = abs(sum(m[3] for m in movements if m[3] and m[3] < 0))
            
            for row in data_with_balance:
                d_row = list(row)
                if d_row[2]: d_row[2] = fix_text(str(d_row[2]))
                if d_row[0]: d_row[0] = fix_text(d_row[0])
                self.tree.insert("", "end", values=d_row)
                self.current_data.append(d_row)
            
            net_flow = total_in - total_out
            self.lbl_total.configure(text=fix_text(f"إجمالي الدخل: {total_in:,.2f} | الإجمالي الخرج: {total_out:,.2f} | صافي التدفق: {net_flow:,.2f} ج.م"))
        
        # 9. BEST SELLING
        elif report_type == fix_text("تقرير الأصناف الأكثر مبيعاً"):
            self.current_columns = ["Item", "Qty_Sold", "Revenue", "Avg_Price"]
            cols_ar = ["الصنف", "الكمية المباعة", "إجمالي المبيعات", "متوسط السعر"]
            
            sql = """SELECT i.name, SUM(id.qty), SUM(id.total), AVG(id.price)
                     FROM invoice_details id
                     JOIN item_details d ON id.item_detail_id = d.id
                     JOIN items i ON d.item_id = i.id
                     JOIN invoices inv ON id.invoice_id = inv.id
                     WHERE inv.date BETWEEN ? AND ?"""
            params = [d_from, d_to]
            
            hd_filter = self.get_hd_filter_sql("d")
            sql += hd_filter
            
            if store != fix_text("كل المخازن"):
                sql += " AND inv.store_id = (SELECT id FROM stores WHERE name = ?)"
                params.append(store)
            
            sql += " GROUP BY i.id ORDER BY SUM(id.qty) DESC LIMIT 50"
            data = self.db.fetch_all(sql, tuple(params))
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=150, anchor="center")
            
            for row in data:
                d_row = list(row)
                d_row[0] = fix_text(d_row[0]) 
                self.tree.insert("", "end", values=d_row)
                self.current_data.append(d_row)
            
            total_revenue = sum(r[2] for r in data if r[2])
            self.lbl_total.configure(text=fix_text(f"عدد الأصناف: {len(data)} | إجمالي المبيعات: {total_revenue:,.2f} ج.م"))
        
        # 10. DAILY SALES
        elif report_type == fix_text("تقرير المبيعات اليومية"):
            self.current_columns = ["Date", "Invoices", "Items", "Total_Sales", "Avg_Invoice"]
            cols_ar = ["التاريخ", "عدد الفواتير", "عدد الأصناف", "إجمالي المبيعات", "متوسط الفاتورة"]
            
            include_hd = self.cb_include_hd.get()
            if not include_hd:
                sql = """SELECT inv.date, COUNT(DISTINCT inv.id), 
                        SUM(CASE WHEN d.barcode NOT LIKE 'HD%' THEN id.qty ELSE 0 END), 
                        SUM(inv.net_total), AVG(inv.net_total)
                        FROM invoices inv
                        LEFT JOIN invoice_details id ON inv.id = id.invoice_id
                        LEFT JOIN item_details d ON id.item_detail_id = d.id
                        WHERE inv.date BETWEEN ? AND ?"""
            else:
                sql = """SELECT inv.date, COUNT(DISTINCT inv.id), SUM(id.qty), SUM(inv.net_total), AVG(inv.net_total)
                         FROM invoices inv
                         LEFT JOIN invoice_details id ON inv.id = id.invoice_id
                         WHERE inv.date BETWEEN ? AND ?"""
            params = [d_from, d_to]
            
            if store != fix_text("كل المخازن"):
                sql += " AND inv.store_id = (SELECT id FROM stores WHERE name = ?)"
                params.append(store)
            
            sql += " GROUP BY inv.date ORDER BY inv.date DESC"
            data = self.db.fetch_all(sql, tuple(params))
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=120, anchor="center")
            
            total_sales = 0
            for row in data:
                self.tree.insert("", "end", values=row)
                self.current_data.append(row)
                total_sales += row[3] if row[3] else 0
            
            avg_daily = total_sales / len(data) if data else 0
            self.lbl_total.configure(text=fix_text(f"إجمالي المبيعات: {total_sales:,.2f} ج.م | متوسط يومي: {avg_daily:,.2f} ج.م"))
        
        # 11. SALES RETURNS REPORT
        elif report_type == fix_text("تقرير مرتجع المبيعات"):
            self.current_columns = ["Return_ID", "Date", "Invoice_ID", "Customer", "Items", "Refund_Amount"]
            cols_ar = ["رقم المرتجع", "التاريخ", "رقم الفاتورة", "العميل", "عدد الأصناف", "قيمة الاسترداد"]
            
            sql = """SELECT r.id, r.date, r.invoice_id, c.name, COUNT(DISTINCT r.item_detail_id), SUM(r.refund_amount)
                     FROM returns r
                     JOIN invoices i ON r.invoice_id = i.id
                     LEFT JOIN customers c ON i.customer_id = c.id
                     WHERE r.date BETWEEN ? AND ?"""
            params = [d_from, d_to]
            
            if store != fix_text("كل المخازن"):
                sql += " AND i.store_id = (SELECT id FROM stores WHERE name = ?)"
                params.append(store)
            
            sql += " GROUP BY r.id ORDER BY r.date DESC"
            data = self.db.fetch_all(sql, tuple(params))
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=120, anchor="center")
            
            total_refunds = 0
            for row in data:
                d_row = list(row)
                if d_row[3]: d_row[3] = fix_text(d_row[3])
                self.tree.insert("", "end", values=d_row)
                self.current_data.append(d_row)
                total_refunds += row[5] if row[5] else 0
            
            self.lbl_total.configure(text=fix_text(f"إجمالي المرتجعات: {total_refunds:,.2f} ج.م | عدد المرتجعات: {len(data)}"))
        
        # 12. DEAD STOCK REPORT
        elif report_type == fix_text("تقرير المخزون الراكد (Dead Stock)"):
            self.current_columns = ["Barcode", "Name", "Store", "Current_Stock", "Last_Sale_Date", "Days_Since_Last_Sale"]
            cols_ar = ["الباركود", "الصنف", "المخزن", "الكمية الحالية", "تاريخ آخر بيع", "أيام منذ آخر بيع"]
            
            try: days_threshold = int(self.ent_days.get() or 30)
            except: days_threshold = 30
            
            sql_base = """SELECT d.barcode, i.name, s.name, ss.quantity, 
                         MAX(inv.date) as last_sale_date,
                         CASE 
                             WHEN MAX(inv.date) IS NULL THEN 9999
                             ELSE (julianday('now') - julianday(MAX(inv.date)))
                         END as days_since
                         FROM store_stock ss
                         JOIN item_details d ON ss.item_detail_id = d.id
                         JOIN items i ON d.item_id = i.id
                         JOIN stores s ON ss.store_id = s.id
                         LEFT JOIN invoice_details id ON d.id = id.item_detail_id
                         LEFT JOIN invoices inv ON id.invoice_id = inv.id
                         WHERE ss.quantity > 0"""
            
            hd_filter = self.get_hd_filter_sql("d")
            sql_base += hd_filter
            
            if store != fix_text("كل المخازن"):
                sql_base += " AND s.name = ?"
                sql = sql_base + " GROUP BY d.id, ss.store_id HAVING days_since > ? OR last_sale_date IS NULL ORDER BY days_since DESC"
                data = self.db.fetch_all(sql, (store, days_threshold))
            else:
                sql = sql_base + " GROUP BY d.id, ss.store_id HAVING days_since > ? OR last_sale_date IS NULL ORDER BY days_since DESC"
                data = self.db.fetch_all(sql, (days_threshold,))
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=120, anchor="center")
            self.tree.column("Name", width=200)
            
            for row in data:
                d_row = list(row)
                d_row[1] = fix_text(d_row[1])  # Name
                d_row[2] = fix_text(d_row[2])  # Store
                if d_row[4]: d_row[4] = str(d_row[4])
                else: d_row[4] = fix_text("لم يباع")
                d_row[5] = int(d_row[5]) if d_row[5] else 9999
                self.tree.insert("", "end", values=d_row)
                self.current_data.append(d_row)
            
            total_stock_value = sum(r[3] for r in data if r[3])
            self.lbl_total.configure(text=fix_text(f"عدد الأصناف الراكدة: {len(data)} | إجمالي الكمية: {total_stock_value}"))

        # 14. NET PROFIT REPORT - FIXED: Uses historical cost_at_sale
        elif report_type == fix_text("تقرير صافي الربح (Net Profit)"):
            self.current_columns = ["Item", "Type", "Amount"]
            cols_ar = ["البند", "النوع", "القيمة"]
            
            sql_sales = "SELECT SUM(net_total) FROM invoices WHERE date BETWEEN ? AND ?"
            total_sales = self.db.fetch_one(sql_sales, (d_from, d_to))[0] or 0
            
            # FIXED: Use cost_at_sale instead of buy_price
            sql_cogs = """SELECT SUM(id.qty * id.cost_at_sale)
                          FROM invoice_details id
                          JOIN invoices i ON id.invoice_id = i.id
                          WHERE i.date BETWEEN ? AND ?"""
            total_cogs = self.db.fetch_one(sql_cogs, (d_from, d_to))[0] or 0
            
            sql_expenses = "SELECT SUM(amount) FROM vouchers WHERE voucher_type='Payment' AND date BETWEEN ? AND ?"
            total_expenses = self.db.fetch_one(sql_expenses, (d_from, d_to))[0] or 0
            
            sql_returns = """SELECT SUM(r.refund_amount) 
                             FROM returns r 
                             WHERE r.date BETWEEN ? AND ?"""
            total_returns = self.db.fetch_one(sql_returns, (d_from, d_to))[0] or 0
            
            net_sales = total_sales - total_returns
            gross_profit = net_sales - total_cogs
            net_profit = gross_profit - total_expenses
            
            data = [
                (fix_text("إجمالي المبيعات"), fix_text("دخل"), total_sales),
                (fix_text("مرتجع المبيعات"), fix_text("خصم من الدخل"), -total_returns),
                (fix_text("صافي المبيعات"), fix_text("دخل صافي"), net_sales),
                (fix_text("تكلفة البضاعة المباعة (COGS)"), fix_text("تكلفة"), -total_cogs),
                (fix_text("مجمل الربح (Gross Profit)"), fix_text("ربح أولي"), gross_profit),
                (fix_text("المصروفات (سندات صرف)"), fix_text("مصروفات"), -total_expenses),
                (fix_text("صافي الربح (Net Profit)"), fix_text("الربح النهائي"), net_profit)
            ]
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=150, anchor="center")
            
            for row in data:
                formatted_row = [row[0], row[1], f"{row[2]:,.2f}"]
                tags = ("bold_row",) if row[0] == fix_text("صافي الربح (Net Profit)") else ()
                self.tree.insert("", "end", values=formatted_row, tags=tags)
                self.current_data.append(list(row))
            
            self.tree.tag_configure("bold_row", font=("Segoe UI", 12, "bold"), background="#D5F5E3")
            color = "#27AE60" if net_profit >= 0 else "#C0392B"
            self.lbl_total.configure(text=fix_text(f"صافي الربح: {net_profit:,.2f} ج.م"), text_color=color)

        # NEW: HIERARCHICAL STOCK REPORT
        elif report_type == fix_text("تقرير جرد تفصيلي (Grouping)"):
            self.tree.configure(show="tree headings") 
            self.current_columns = ["Description", "Quantity", "Level"]
            cols_ar = ["الصنف / التفاصيل", "الكمية"]
            
            self.tree["columns"] = ["Total_Qty"]
            self.tree.heading("#0", text=fix_text("الصنف / التفاصيل"))
            self.tree.column("#0", width=400, anchor="w")
            self.tree.heading("Total_Qty", text=fix_text("الكمية"))
            self.tree.column("Total_Qty", width=150, anchor="center")
            
            sql = """SELECT i.id, i.name, c.name, sz.name, SUM(ss.quantity)
                     FROM store_stock ss
                     JOIN item_details d ON ss.item_detail_id = d.id
                     JOIN items i ON d.item_id = i.id
                     LEFT JOIN colors c ON d.color_id = c.id
                     LEFT JOIN sizes sz ON d.size_id = sz.id
                     LEFT JOIN stores st ON ss.store_id = st.id
                     WHERE ss.quantity > 0"""
            
            params = []
            if store != fix_text("كل المخازن"):
                sql += " AND st.name = ?"
                params.append(store)
            
            sql += self.get_hd_filter_sql("d")
            sql += " GROUP BY i.id, c.id, d.size_id ORDER BY i.name, c.name"
            raw_data = self.db.fetch_all(sql, tuple(params))
            
            hierarchy = {}
            for row in raw_data:
                item_id, item_name, color_name, size_name, qty = row
                item_name = fix_text(item_name)
                color_name = fix_text(color_name or "سادة")
                size_name = fix_text(size_name or "One Size")
                qty = float(qty)
                
                if item_id not in hierarchy:
                    hierarchy[item_id] = {"name": item_name, "total": 0, "colors": {}}
                
                h_item = hierarchy[item_id]
                h_item["total"] += qty
                
                if color_name not in h_item["colors"]:
                    h_item["colors"][color_name] = {"total": 0, "sizes": []}
                
                h_color = h_item["colors"][color_name]
                h_color["total"] += qty
                h_color["sizes"].append((size_name, qty))
            
            total_grand = 0
            
            for item_id, h_item in hierarchy.items():
                item_text = h_item['name']
                parent_id = self.tree.insert("", "end", text=item_text, values=[h_item["total"]], open=False)
                self.current_data.append([item_text, h_item["total"], 0]) 
                total_grand += h_item["total"]
                
                for color_name, h_color in h_item["colors"].items():
                    color_text = f"🎨 {color_name}"
                    color_id = self.tree.insert(parent_id, "end", text=color_text, values=[h_color["total"]], open=False)
                    self.current_data.append([color_text, h_color["total"], 1])
                    
                    for size_name, size_qty in h_color["sizes"]:
                        size_text = f"📏 {size_name}"
                        self.tree.insert(color_id, "end", text=size_text, values=[size_qty])
                        self.current_data.append([size_text, size_qty, 2])
            
            self.lbl_total.configure(text=fix_text(f"إجمالي عدد القطع: {total_grand}"))
            
        else:
            self.tree.configure(show="headings")
            
        # 13. SALES BY CHANNEL & DELEGATE
        if report_type == fix_text("تقرير أداء المندوبين"):
            self.current_columns = ["Channel", "Delegate", "Total_Invoices", "Total_Revenue"]
            cols_ar = ["القناة", "المندوب", "عدد الفواتير", "إجمالي المبيعات"]
            
            include_hd = self.cb_include_hd.get()
            if not include_hd:
                sql = """SELECT i.channel, i.delegate_name, COUNT(DISTINCT i.id), 
                        COALESCE(SUM(CASE WHEN d.barcode NOT LIKE 'HD%' THEN id.total ELSE 0 END), 0)
                        FROM invoices i
                        LEFT JOIN invoice_details id ON i.id = id.invoice_id
                        LEFT JOIN item_details d ON id.item_detail_id = d.id
                        WHERE i.date BETWEEN ? AND ?"""
                params = [d_from, d_to]
                if store != fix_text("كل المخازن"):
                    sql += " AND i.store_id = (SELECT id FROM stores WHERE name = ?)"
                    params.append(store)
                sql += " GROUP BY i.channel, i.delegate_name HAVING COALESCE(SUM(CASE WHEN d.barcode NOT LIKE 'HD%' THEN id.total ELSE 0 END), 0) > 0 ORDER BY COALESCE(SUM(CASE WHEN d.barcode NOT LIKE 'HD%' THEN id.total ELSE 0 END), 0) DESC"
            else:
                sql = """SELECT i.channel, i.delegate_name, COUNT(DISTINCT i.id), SUM(i.net_total)
                         FROM invoices i
                         WHERE i.date BETWEEN ? AND ?"""
                params = [d_from, d_to]
                if store != fix_text("كل المخازن"):
                    sql += " AND i.store_id = (SELECT id FROM stores WHERE name = ?)"
                    params.append(store)
                sql += " GROUP BY i.channel, i.delegate_name ORDER BY SUM(i.net_total) DESC"
            
            data = self.db.fetch_all(sql, tuple(params))
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=150, anchor="center")
            
            for row in data:
                d_row = list(row)
                if d_row[0]: d_row[0] = fix_text(d_row[0])
                if d_row[1]: d_row[1] = fix_text(d_row[1])
                self.tree.insert("", "end", values=d_row)
                self.current_data.append(d_row)
            
            total_revenue = sum(r[3] for r in data if r[3])
            self.lbl_total.configure(text=fix_text(f"إجمالي المبيعات: {total_revenue:,.2f} ج.م | عدد المجموعات: {len(data)}"))
        
        # 14. CUSTOMER STATEMENT
        elif report_type == fix_text("كشف حساب عميل"):
            customer_name = self.cb_customer.get().strip()
            if not customer_name:
                messagebox.showerror("Error", "Please select customer")
                return
            
            self.current_columns = ["Date", "Type", "Reference", "Debit", "Credit", "Balance"]
            cols_ar = ["التاريخ", "نوع العملية", "رقم المرجع", "مدين", "دائن", "الرصيد"]
            
            cust_res = self.db.fetch_one("SELECT id FROM customers WHERE name LIKE ?", (f"%{customer_name}%",))
            if not cust_res:
                messagebox.showerror("Error", f"Customer not found: {customer_name}")
                return
            
            cust_id = cust_res[0]
            
            sql_invoices = """SELECT date, 'فاتورة', ('فاتورة #' || id), net_total, 0, NULL
                              FROM invoices
                              WHERE customer_id = ? AND date BETWEEN ? AND ?
                              ORDER BY date, id"""
            invoices = self.db.fetch_all(sql_invoices, (cust_id, d_from, d_to))
            
            sql_returns = """SELECT r.date, 'مرتجع', r.invoice_id, 0, r.refund_amount, NULL
                             FROM returns r
                             JOIN invoices i ON r.invoice_id = i.id
                             WHERE i.customer_id = ? AND r.date BETWEEN ? AND ?
                             GROUP BY r.id
                             ORDER BY r.date, r.id"""
            returns = self.db.fetch_all(sql_returns, (cust_id, d_from, d_to))
            
            sql_receipts = """SELECT date, 'سند قبض', ('سند #' || id || ' - ' || COALESCE(description, '')), 0, amount, NULL
                              FROM vouchers
                              WHERE customer_id = ? AND voucher_type = 'Receipt' AND date BETWEEN ? AND ?
                              ORDER BY date, id"""
            receipts = self.db.fetch_all(sql_receipts, (cust_id, d_from, d_to))
                         
            all_transactions = []
            for inv in invoices: all_transactions.append(list(inv))
            for ret in returns: all_transactions.append(list(ret))
            for rec in receipts: all_transactions.append(list(rec))
            
            all_transactions.sort(key=lambda x: (x[0], x[2]))
            
            balance = 0.0
            for trans in all_transactions:
                debit = trans[3] if trans[3] else 0
                credit = trans[4] if trans[4] else 0
                balance += debit - credit
                trans[5] = balance
            
            self.tree["columns"] = self.current_columns
            for col, name in zip(self.current_columns, cols_ar):
                self.tree.heading(col, text=fix_text(name))
                self.tree.column(col, width=120, anchor="center")
            
            for row in all_transactions:
                d_row = list(row)
                d_row[1] = fix_text(d_row[1])
                self.tree.insert("", "end", values=d_row)
                self.current_data.append(d_row)
            
            final_balance = balance
            total_debit = sum(t[3] for t in all_transactions)
            total_credit = sum(t[4] for t in all_transactions)
            self.lbl_total.configure(text=fix_text(f"إجمالي المدين: {total_debit:,.2f} | إجمالي الدائن: {total_credit:,.2f} | الرصيد النهائي: {final_balance:,.2f} ج.م"))

    def export_excel(self):
        if not self.current_data: 
            messagebox.showerror("Error", "No data to export")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if path:
            try:
                export_list = []
                if self.current_report_type == fix_text("تقرير جرد تفصيلي (Grouping)"):
                    headers = [fix_text("الصنف / التفاصيل"), fix_text("الكمية")]
                    for row in self.current_data:
                        export_list.append([row[0], row[1]])
                else:
                    headers = [self.tree.heading(c)["text"] for c in self.current_columns if c != "Level"]
                    export_list = self.current_data

                df = pd.DataFrame(export_list, columns=headers)
                df.to_excel(path, index=False, engine='openpyxl')
                messagebox.showinfo("Success", "Excel file saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")

    def export_pdf(self):
        if not self.current_data: 
            messagebox.showerror("Error", "No data to export")
            return
        
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "ReportLab library not found.\nPlease install: pip install reportlab")
            return
            
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path: return
        
        try:
            # Register Font
            font_path = "C:\\Windows\\Fonts\\arial.ttf" 
            if not os.path.exists(font_path): font_path = "C:\\Windows\\Fonts\\tahoma.ttf"
            
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
                font_name = 'ArabicFont'
            else:
                font_name = 'Helvetica'
            
            try:
               doc = SimpleDocTemplate(path, pagesize=A4)
            except NameError:
               # In case imports failed but REPORTLAB_AVAILABLE is True (edge case)
               from app.utils import SimpleDocTemplate, A4, Table, TableStyle, Paragraph, Spacer, colors, getSampleStyleSheet, ParagraphStyle
               doc = SimpleDocTemplate(path, pagesize=A4)

            elements = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(name='ArabicTitle', parent=styles['Title'], fontName=font_name, fontSize=18, alignment=1)
            elements.append(Paragraph(self.current_report_type, title_style))
            elements.append(Spacer(1, 20))
            
            if self.current_report_type == fix_text("تقرير جرد تفصيلي (Grouping)"):
                data_rows = [["Description / Item", "Quantity"]]
                
                table_styles = [
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ]
                
                for idx, row in enumerate(self.current_data):
                    desc, qty, level = row
                    row_idx = idx + 1
                    data_rows.append([desc, str(qty)])
                    
                    if level == 0:
                        table_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightgrey))
                        table_styles.append(('FONTSIZE', (0, row_idx), (-1, row_idx), 12))
                        table_styles.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.black))
                        table_styles.append(('BottomPadding', (0, row_idx), (-1, row_idx), 6))
                    elif level == 1:
                        table_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.whitesmoke))
                        table_styles.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.darkblue))
                        table_styles.append(('LEFTPADDING', (0, row_idx), (0, row_idx), 20))
                    elif level == 2:
                        table_styles.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.black))
                        table_styles.append(('LEFTPADDING', (0, row_idx), (0, row_idx), 40))

                t = Table(data_rows, colWidths=[350, 100])
                t.setStyle(TableStyle(table_styles))
                elements.append(t)

            else:
                headers = [self.tree.heading(c)["text"] for c in self.current_columns if c != "Level"]
                data_rows = [headers]
                for row in self.current_data:
                    data_rows.append([str(c) for c in row])
                
                t = Table(data_rows, repeatRows=1)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(t)
            
            if self.lbl_total.cget("text"):
                elements.append(Spacer(1, 20))
                elements.append(Paragraph(self.lbl_total.cget("text"), ParagraphStyle(name='Sum', fontName=font_name, alignment=1)))
            
            doc.build(elements)
            messagebox.showinfo("Success", "PDF saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Print Error", f"Make sure file is closed if open.\nError: {e}")
