
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import os

from app.database import DB
from app.utils import fix_text, REPORTLAB_AVAILABLE, BARCODE_AVAILABLE

if REPORTLAB_AVAILABLE:
    from app.utils import (
        SimpleDocTemplate, A4, Table, TableStyle, Paragraph, Spacer, 
        colors, getSampleStyleSheet, ParagraphStyle, pdfmetrics, TTFont
    )
    from reportlab.platypus import Image as RLImage

if BARCODE_AVAILABLE:
    from app.utils import barcode, ImageWriter

class StockPage(ctk.CTkFrame):
    def __init__(self, parent, user_role="Admin", controller=None):
        super().__init__(parent)
        self.user_role = user_role
        self.controller = controller
        self.db = DB()
        
        # Fonts
        self.AR_FONT = ("Segoe UI", 12, "bold")
        self.AR_FONT_NORM = ("Segoe UI", 12)
        
        # --- Header ---
        header = ctk.CTkFrame(self, height=50)
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text=fix_text("إدارة الأصناف والمخزون"), font=("Segoe UI", 20, "bold")).pack(side="right", padx=20)
        if self.user_role == "Admin":
            ctk.CTkButton(header, text=fix_text("+ إضافة صنف جديد"), command=self.open_add_popup, fg_color="#27AE60", font=self.AR_FONT, width=150).pack(side="left", padx=10)

        # --- Controls & Filters ---
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        # Search
        ctk.CTkButton(ctrl_frame, text=fix_text("بحث"), command=self.load, font=self.AR_FONT, width=60).pack(side="right", padx=5)
        self.ent_search = ctk.CTkEntry(ctrl_frame, placeholder_text=fix_text("بحث بالاسم أو الباركود..."), width=200, font=self.AR_FONT_NORM, justify="right")
        self.ent_search.pack(side="right", padx=5)
        self.ent_search.bind("<KeyRelease>", lambda e: self.load())
        
        # Filter
        ctk.CTkLabel(ctrl_frame, text=fix_text(":عرض"), font=self.AR_FONT).pack(side="right", padx=(5, 15))
        filter_options = [fix_text("الكل"), fix_text("منتجات فقط (No HD)"), fix_text("تصميمات فقط (HD)")]
        self.cb_filter = ctk.CTkComboBox(
            ctrl_frame, 
            values=filter_options, 
            width=170, 
            font=self.AR_FONT_NORM, 
            dropdown_font=self.AR_FONT_NORM,
            command=lambda x: self.load()
        )
        self.cb_filter.pack(side="right", padx=5)
        self.cb_filter.set(filter_options[0]) 
        
        # Bulk Update (Admin only)
        if self.user_role == "Admin":
            ctk.CTkButton(ctrl_frame, text=fix_text("تطبيق"), command=self.bulk_update, fg_color="#E67E22", font=self.AR_FONT, width=60).pack(side="left", padx=5)
            self.ent_bulk = ctk.CTkEntry(ctrl_frame, width=100, placeholder_text="0.00", font=self.AR_FONT_NORM)
            self.ent_bulk.pack(side="left", padx=5)
            ctk.CTkLabel(ctrl_frame, text=fix_text("تحديث سعر البيع:"), font=self.AR_FONT).pack(side="left", padx=5)
        
        # Print Barcode Button
        if BARCODE_AVAILABLE:
            ctk.CTkButton(ctrl_frame, text=fix_text("🏷️طباعة باركود"), command=self.print_barcode, 
                         fg_color="#9B59B6", font=self.AR_FONT, width=120).pack(side="left", padx=10)

        # --- Treeview ---
        self.tree = ttk.Treeview(self, columns=("ID", "Barcode", "Name", "Color", "Size", "TotalStock", "Cost", "Price"), show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        cols = [
            ("ID", 50), ("Barcode", 120), ("Name", 200), 
            ("Color", 80), ("Size", 80), 
            ("TotalStock", 100), ("Cost", 100), ("Price", 100)
        ]
        headers = ["م", "الباركود", "اسم الصنف", "اللون", "المقاس", "الرصيد", "التكلفة", "سعر البيع"]
        
        for (col, w), h in zip(cols, headers):
            self.tree.heading(col, text=fix_text(h))
            self.tree.column(col, width=w, anchor="center" if col != "Name" else "e")
            
        self.load()

        # --- Footer (Edit & Delete Buttons - Admin only) ---
        footer = ctk.CTkFrame(self, height=50)
        footer.pack(fill="x", padx=10, pady=10)
        
        if self.user_role == "Admin":
            ctk.CTkButton(footer, text=fix_text("تعديل الصنف المحدد"), command=self.edit_selected, 
                          fg_color="#3498DB", font=self.AR_FONT, width=150).pack(side="left", padx=20)
                          
            ctk.CTkButton(footer, text=fix_text("حذف الصنف المحدد"), command=self.delete_selected, 
                          fg_color="#C0392B", font=self.AR_FONT, width=150).pack(side="right", padx=20)

    def load(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        search = self.ent_search.get().strip()
        
        current_filter = self.cb_filter.get()
        filter_mode = "All"
        if "HD" in current_filter and "No" in current_filter: filter_mode = "Products"
        elif "HD" in current_filter: filter_mode = "Designs"
        
        sql = """
            SELECT d.id, d.barcode, i.name, 
                   IFNULL(c.name, '-'), IFNULL(s.name, '-'), 
                   IFNULL(SUM(ss.quantity), 0), d.buy_price, d.sell_price 
            FROM item_details d 
            JOIN items i ON d.item_id=i.id 
            LEFT JOIN colors c ON d.color_id=c.id 
            LEFT JOIN sizes s ON d.size_id=s.id 
            LEFT JOIN store_stock ss ON ss.item_detail_id=d.id 
            WHERE (i.name LIKE ? OR d.barcode LIKE ?)
        """
        
        if filter_mode == "Products": sql += " AND d.barcode NOT LIKE 'HD%'"
        elif filter_mode == "Designs": sql += " AND d.barcode LIKE 'HD%'"
            
        sql += " GROUP BY d.id ORDER BY d.id DESC"
        
        param = f"%{search}%"
        for r in self.db.fetch_all(sql, (param, param)):
            row_data = list(r)
            row_data[2] = fix_text(row_data[2]) # Name
            row_data[3] = fix_text(row_data[3]) # Color
            row_data[4] = fix_text(row_data[4]) # Size
            self.tree.insert("", "end", values=row_data)
    
    def bulk_update(self):
        if self.user_role != "Admin": return
        try: p = float(self.ent_bulk.get())
        except: return messagebox.showerror("Error", "Invalid price")
        
        ids = [self.tree.item(i)['values'][0] for i in self.tree.get_children()]
        if not ids: return
        if not messagebox.askyesno(fix_text("تأكيد"), fix_text(f"هل أنت متأكد من تحديث سعر {len(ids)} صنف؟")): return
        
        placeholders = ','.join('?' * len(ids))
        self.db.execute(f"UPDATE item_details SET sell_price = ? WHERE id IN ({placeholders})", [p] + ids)
        messagebox.showinfo("Success", "Prices updated"); self.load()
        if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
    
    def print_barcode(self):
        if not BARCODE_AVAILABLE or not REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "Barcode/PDF libraries not installed")
            return
        
        sel = self.tree.selection()
        if not sel: return messagebox.showerror("Error", "Select item to print")
        
        item_id = self.tree.item(sel[0])['values'][0]
        sql = """SELECT d.barcode, i.name, d.sell_price, s.name 
                 FROM item_details d
                 JOIN items i ON d.item_id = i.id
                 LEFT JOIN store_stock ss ON d.id = ss.item_detail_id
                 LEFT JOIN stores s ON ss.store_id = s.id
                 WHERE d.id = ?
                 LIMIT 1"""
        res = self.db.fetch_one(sql, (item_id,))
        if not res: return messagebox.showerror("Error", "Item not found")
        
        barcode_val, item_name, price, store_name = res[0], res[1], res[2] or 0, res[3] or "N/A"
        
        qty_popup = ctk.CTkToplevel(self)
        qty_popup.title("Print Barcode Labels")
        qty_popup.geometry("300x150")
        ctk.CTkLabel(qty_popup, text="Number of Labels:", font=("Segoe UI", 14)).pack(pady=20)
        ent_qty = ctk.CTkEntry(qty_popup, width=100, font=("Segoe UI", 14))
        ent_qty.pack(pady=10)
        ent_qty.insert(0, "1")
        ent_qty.focus()
        
        def generate_labels():
            try:
                qty = int(ent_qty.get())
                if qty <= 0: return messagebox.showerror("Error", "Quantity must be greater than zero")
                qty_popup.destroy()
                self._generate_barcode_pdf(barcode_val, item_name, price, store_name, qty)
            except ValueError: messagebox.showerror("Error", "Please enter a valid number")
        
        ent_qty.bind("<Return>", lambda e: generate_labels())
        ctk.CTkButton(qty_popup, text="PRINT", command=generate_labels, fg_color="#27AE60", font=("Segoe UI", 14)).pack(pady=10)
    
    def _generate_barcode_pdf(self, barcode_val, item_name, price, store_name, qty):
        try:
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile=f"barcode_{barcode_val}.pdf")
            if not path: return
            
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(barcode_val, writer=ImageWriter())
            temp_barcode_path = f"temp_barcode_{barcode_val}.png"
            barcode_instance.save(f"temp_barcode_{barcode_val}", options={'format': 'PNG', 'module_width': 0.5, 'module_height': 10})
            os.rename(f"temp_barcode_{barcode_val}.png", temp_barcode_path)
            
            font_path = "C:\\Windows\\Fonts\\arial.ttf"
            if not os.path.exists(font_path): font_path = "C:\\Windows\\Fonts\\tahoma.ttf"
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
                font_name = 'ArabicFont'
            else: font_name = 'Helvetica'
            
            doc = SimpleDocTemplate(path, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(name='ArabicTitle', parent=styles['Title'], fontName=font_name, fontSize=16, alignment=1)
            normal_style = ParagraphStyle(name='ArabicNormal', parent=styles['Normal'], fontName=font_name, fontSize=12, alignment=1)
            
            from reportlab.lib.units import mm
            label_width = 90 * mm
            # label_height = 50 * mm
            
            for i in range(qty):
                if i > 0 and i % 4 == 0: elements.append(Spacer(1, 20))
                label_data = [
                    [Paragraph(store_name, normal_style)],
                    [Paragraph(item_name, title_style)],
                    [RLImage(temp_barcode_path, width=80*mm, height=20*mm)],
                    [Paragraph(f"{price:.2f} EGP", normal_style)]
                ]
                label_table = Table(label_data, colWidths=label_width)
                label_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(label_table)
                elements.append(Spacer(1, 5))
            
            doc.build(elements)
            os.remove(temp_barcode_path)
            messagebox.showinfo("Success", f"{qty} labels created")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")
            if os.path.exists(temp_barcode_path): os.remove(temp_barcode_path)

    def delete_selected(self):
        if self.user_role != "Admin": return
        sel = self.tree.selection()
        if not sel: return messagebox.showerror(fix_text("تنبيه"), fix_text("اختر صنفاً للحذف"))
        
        item_id = self.tree.item(sel[0])['values'][0]
        used_sales = self.db.fetch_one("SELECT 1 FROM invoice_details WHERE item_detail_id=?", (item_id,))
        used_purchase = self.db.fetch_one("SELECT 1 FROM purchase_details WHERE item_detail_id=?", (item_id,))
        
        if used_sales or used_purchase:
            return messagebox.showerror("Error", "Cannot delete this item (used in invoices).\nYou can edit its name or price instead.")
            
        if not messagebox.askyesno(fix_text("تأكيد الحذف"), fix_text(f"هل أنت متأكد من حذف الصنف نهائياً؟")): return
            
        try:
            self.db.execute("DELETE FROM store_stock WHERE item_detail_id=?", (item_id,))
            self.db.execute("DELETE FROM item_details WHERE id=?", (item_id,))
            messagebox.showinfo("Success", "Deleted successfully"); self.load()
            if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
        except Exception as e: messagebox.showerror("Error", f"Error: {e}")

    def edit_selected(self):
        if self.user_role != "Admin": return
        sel = self.tree.selection()
        if not sel: return messagebox.showerror(fix_text("تنبيه"), fix_text("اختر صنفاً للتعديل"))
        item_id = self.tree.item(sel[0])['values'][0]
        self.open_add_popup(item_id)

    def open_add_popup(self, item_id=None):
        pop = ctk.CTkToplevel(self)
        title = "تعديل صنف" if item_id else "إضافة صنف جديد"
        pop.title(fix_text(title))
        pop.geometry("450x600")
        pop.grab_set()
        
        def add_input(lbl):
            ctk.CTkLabel(pop, text=fix_text(lbl), font=self.AR_FONT).pack(anchor="e", padx=20, pady=(10,0))
            e = ctk.CTkEntry(pop, width=300, font=self.AR_FONT_NORM, justify="right")
            e.pack(padx=20, pady=5)
            return e

        e_barcode = add_input(":الباركود")
        e_name = add_input(":اسم الصنف")
        e_color = add_input(":اللون")
        e_size = add_input(":المقاس")
        e_cost = add_input(":سعر التكلفة")
        e_price = add_input(":سعر البيع")
        
        if item_id:
            sql = """SELECT d.barcode, i.name, c.name, s.name, d.buy_price, d.sell_price 
                     FROM item_details d 
                     JOIN items i ON d.item_id=i.id 
                     LEFT JOIN colors c ON d.color_id=c.id 
                     LEFT JOIN sizes s ON d.size_id=s.id 
                     WHERE d.id=?"""
            data = self.db.fetch_one(sql, (item_id,))
            if data:
                e_barcode.insert(0, data[0])
                e_name.insert(0, data[1])
                e_color.insert(0, data[2] or "")
                e_size.insert(0, data[3] or "")
                e_cost.insert(0, str(data[4]))
                e_price.insert(0, str(data[5]))
        else:
            e_cost.insert(0, "0"); e_price.insert(0, "0")

        def save():
            barcode = e_barcode.get().strip().upper() 
            name = e_name.get().strip()
            if not barcode or not name: return messagebox.showerror("Error", "Barcode and item name are required!")
            
            try:
                res = self.db.fetch_one("SELECT id FROM items WHERE name=?", (name,))
                i_id = res[0] if res else self.db.execute("INSERT INTO items (name) VALUES (?)", (name,))
                
                color = e_color.get().strip(); c_id = None
                if color:
                    res = self.db.fetch_one("SELECT id FROM colors WHERE name=?", (color,))
                    c_id = res[0] if res else self.db.execute("INSERT INTO colors (name) VALUES (?)", (color,))
                
                size = e_size.get().strip(); s_id = None
                if size:
                    res = self.db.fetch_one("SELECT id FROM sizes WHERE name=?", (size,))
                    s_id = res[0] if res else self.db.execute("INSERT INTO sizes (name) VALUES (?)", (size,))
                
                cost = float(e_cost.get() or 0); price = float(e_price.get() or 0)
                
                if item_id:
                    conflict = self.db.fetch_one("SELECT id FROM item_details WHERE barcode=? AND id!=?", (barcode, item_id))
                    if conflict: return messagebox.showerror("Error", "Barcode already used for another item!")
                    self.db.execute("""UPDATE item_details SET item_id=?, barcode=?, color_id=?, size_id=?, buy_price=?, sell_price=? WHERE id=?""", (i_id, barcode, c_id, s_id, cost, price, item_id))
                    messagebox.showinfo("Success", "Updated successfully")
                else:
                    exists = self.db.fetch_one("SELECT id FROM item_details WHERE barcode=?", (barcode,))
                    if exists: return messagebox.showerror("Error", "Barcode already exists!")
                    self.db.execute("""INSERT INTO item_details (item_id, barcode, color_id, size_id, buy_price, sell_price) VALUES (?, ?, ?, ?, ?, ?)""", (i_id, barcode, c_id, s_id, cost, price))
                    messagebox.showinfo("Success", "Item added successfully")
                
                pop.destroy(); self.load() 
                if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
            except Exception as e: messagebox.showerror("Error", f"Error: {e}")

        ctk.CTkButton(pop, text=fix_text("حفظ"), command=save, fg_color="#27AE60", font=self.AR_FONT).pack(pady=30, fill="x", padx=40)
