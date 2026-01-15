
import customtkinter as ctk
from tkinter import ttk, messagebox
from app.database import DB
from app.utils import fix_text

class SuppliersPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.db = DB()
        
        header = ctk.CTkFrame(self, height=50)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text=fix_text("إدارة الموردين"), font=("Arial", 20, "bold")).pack(side="left", padx=20)
        ctk.CTkButton(header, text=fix_text("+ إضافة مورد"), command=self.add_supplier, fg_color="#8E44AD", width=150, font=("Arial", 12)).pack(side="right", padx=10)
        
        filter_frm = ctk.CTkFrame(self)
        filter_frm.pack(fill="x", padx=10, pady=5)
        self.ent_search = ctk.CTkEntry(filter_frm, placeholder_text=fix_text("البحث بالاسم أو الهاتف..."), font=("Arial", 12))
        self.ent_search.pack(side="left", fill="x", expand=True, padx=5)
        self.ent_search.bind("<KeyRelease>", lambda e: self.load())
        ctk.CTkButton(filter_frm, text=fix_text("بحث"), command=self.load, width=100, font=("Arial", 12)).pack(side="left", padx=5)
        
        self.tree = ttk.Treeview(self, columns=("ID", "Name", "Phone", "Address", "Email"), show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        cols = [("ID", 50), ("Name", 200), ("Phone", 150), ("Address", 250), ("Email", 200)]
        for c, w in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center" if c=="ID" else "w")
            
        footer = ctk.CTkFrame(self, height=50)
        footer.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(footer, text=fix_text("تعديل المورد المحدد"), command=self.edit_supplier, fg_color="#3B8ED0", font=("Arial", 12)).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(footer, text=fix_text("حذف المورد المحدد"), command=self.delete_supplier, fg_color="#C0392B", font=("Arial", 12)).pack(side="right", padx=10, pady=10)
        
        self.load()

    def load(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        search = self.ent_search.get().strip()
        sql = "SELECT id, name, phone, address, email FROM suppliers"
        params = ()
        if search:
            sql += " WHERE name LIKE ? OR phone LIKE ?"
            params = (f"%{search}%", f"%{search}%")
        sql += " ORDER BY id DESC"
        results = self.db.fetch_all(sql, params)
        for r in results:
            self.tree.insert("", "end", values=r)

    def add_supplier(self):
        self.open_popup(fix_text("إضافة مورد جديد"))

    def edit_supplier(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showerror("Error", "Please select a supplier first")
        item = self.tree.item(sel[0])
        record_id = item['values'][0]
        data = self.db.fetch_one("SELECT id, name, phone, address, email, notes FROM suppliers WHERE id=?", (record_id,))
        if data:
            self.open_popup(fix_text("تعديل بيانات مورد"), data)

    def delete_supplier(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showerror("Error", "Please select a supplier first")
        if messagebox.askyesno(fix_text("تأكيد الحذف"), fix_text("هل أنت متأكد من حذف هذا المورد؟")):
            try:
                rec_id = self.tree.item(sel[0])['values'][0]
                self.db.execute("DELETE FROM suppliers WHERE id=?", (rec_id,))
                messagebox.showinfo("Success", "Supplier deleted successfully")
                self.load()
                if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
            except Exception as e:
                messagebox.showerror("Error", f"Cannot delete supplier (may be linked to invoices)\n\nDetails: {e}")

    def open_popup(self, title, data=None):
        pop = ctk.CTkToplevel(self)
        pop.title(title)
        pop.geometry("450x550")
        pop.grab_set()
        
        def create_entry(lbl, val=""):
            ctk.CTkLabel(pop, text=fix_text(lbl), font=("Arial", 12, "bold")).pack(anchor="w", padx=20, pady=(10,0))
            e = ctk.CTkEntry(pop, width=400, font=("Arial", 12))
            e.pack(padx=20, pady=5)
            if val: e.insert(0, str(val))
            return e

        e_name = create_entry("اسم المورد:", data[1] if data else "")
        e_phone = create_entry("رقم الهاتف:", data[2] if data else "")
        e_addr = create_entry("العنوان:", data[3] if data else "")
        e_email = create_entry("البريد الإلكتروني:", data[4] if data else "")
        
        ctk.CTkLabel(pop, text=fix_text("ملاحظات:"), font=("Arial", 12, "bold")).pack(anchor="w", padx=20, pady=(10,0))
        e_notes = ctk.CTkTextbox(pop, width=400, height=80, font=("Arial", 12))
        e_notes.pack(padx=20, pady=5)
        if data and data[5]: e_notes.insert("1.0", str(data[5]))
        
        def save():
            name = e_name.get().strip()
            if not name: return messagebox.showerror("Error", "Supplier name required")
            vals = (name, e_phone.get().strip(), e_addr.get().strip(), e_email.get().strip(), e_notes.get("1.0", "end").strip())
            if data:
                self.db.execute("UPDATE suppliers SET name=?, phone=?, address=?, email=?, notes=? WHERE id=?", vals + (data[0],))
            else:
                self.db.execute("INSERT INTO suppliers (name, phone, address, email, notes) VALUES (?,?,?,?,?)", vals)
            messagebox.showinfo("Success", "Saved successfully")
            pop.destroy()
            self.load()
            if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
            
        ctk.CTkButton(pop, text=fix_text("حفظ البيانات"), command=save, fg_color="#27AE60", height=40, font=("Arial", 12)).pack(pady=20, fill="x", padx=20)
