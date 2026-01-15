
import customtkinter as ctk
from tkinter import ttk, messagebox
from app.utils import fix_text
from app.database import DB
from app.auth import LoginManager

class UsersPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.db = DB()
        self.auth = LoginManager()
        
        # Fonts
        self.AR_FONT = ("Segoe UI", 12, "bold")
        self.AR_FONT_NORM = ("Segoe UI", 12)
        
        # --- Header ---
        header = ctk.CTkFrame(self, height=60)
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text=fix_text("إدارة المستخدمين"), font=("Segoe UI", 20, "bold")).pack(side="right", padx=20)
        ctk.CTkButton(header, text=fix_text("+ إضافة مستخدم جديد"), command=self.open_add_popup, 
                     fg_color="#27AE60", font=self.AR_FONT, width=150).pack(side="left", padx=10)
        
        # --- Treeview ---
        self.tree = ttk.Treeview(self, columns=("ID", "Username", "Role"), show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        headers = ["م", "اسم المستخدم", "الدور"]
        widths = [50, 200, 150]
        for (col, w), h in zip([("ID", widths[0]), ("Username", widths[1]), ("Role", widths[2])], headers):
            self.tree.heading(col, text=fix_text(h))
            self.tree.column(col, width=w, anchor="center")
        
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())
        
        # --- Footer Buttons ---
        footer = ctk.CTkFrame(self, height=50)
        footer.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(footer, text=fix_text("تغيير كلمة المرور"), command=self.change_password, 
                     fg_color="#3498DB", font=self.AR_FONT, width=150).pack(side="left", padx=20)
        ctk.CTkButton(footer, text=fix_text("حذف المستخدم"), command=self.delete_selected, 
                     fg_color="#C0392B", font=self.AR_FONT, width=150).pack(side="right", padx=20)
        
        self.load()
    
    def load(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        users = self.db.fetch_all("SELECT id, username, role FROM users ORDER BY id")
        for user in users:
            row = list(user)
            row[2] = fix_text(row[2])  # Role
            self.tree.insert("", "end", values=row)
    
    def open_add_popup(self):
        pop = ctk.CTkToplevel(self)
        pop.title(fix_text("إضافة مستخدم جديد"))
        pop.geometry("400x300")
        pop.grab_set()
        
        ctk.CTkLabel(pop, text=fix_text("اسم المستخدم:"), font=self.AR_FONT).pack(anchor="e", padx=40, pady=(30, 5))
        ent_username = ctk.CTkEntry(pop, width=250, font=self.AR_FONT_NORM)
        ent_username.pack(pady=5)
        ent_username.focus()
        
        ctk.CTkLabel(pop, text=fix_text("كلمة المرور:"), font=self.AR_FONT).pack(anchor="e", padx=40, pady=(15, 5))
        ent_password = ctk.CTkEntry(pop, width=250, show="*", font=self.AR_FONT_NORM)
        ent_password.pack(pady=5)
        
        ctk.CTkLabel(pop, text=fix_text("الدور:"), font=self.AR_FONT).pack(anchor="e", padx=40, pady=(15, 5))
        cb_role = ctk.CTkComboBox(pop, values=[fix_text("Admin"), fix_text("Sales")], 
                                  width=250, font=self.AR_FONT_NORM, dropdown_font=self.AR_FONT_NORM)
        cb_role.pack(pady=5)
        cb_role.set(fix_text("Sales"))
        
        def save():
            username = ent_username.get().strip()
            password = ent_password.get().strip()
            role = cb_role.get()
            
            if not username or not password:
                messagebox.showerror("Error", "Please enter all data")
                return
            
            # Check if username already exists
            existing = self.db.fetch_one("SELECT id FROM users WHERE username=?", (username,))
            if existing:
                messagebox.showerror("Error", "Username already exists")
                return
            
            # Convert role back to English
            role_en = "Admin" if role == fix_text("Admin") else "Sales"
            
            # Use Auth Manager to create user with hashed password
            if self.auth.create_user(username, password, role_en):
                messagebox.showinfo("Success", "User added successfully")
                pop.destroy()
                self.load()
            else:
                messagebox.showerror("Error", "Error creating user")
        
        ctk.CTkButton(pop, text=fix_text("حفظ"), command=save, fg_color="#27AE60", 
                     font=self.AR_FONT, width=250, height=40).pack(pady=30)
        
        ent_password.bind("<Return>", lambda e: save())
        ent_username.bind("<Return>", lambda e: ent_password.focus())
    
    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Please select a user")
            return
        user_id = self.tree.item(sel[0])['values'][0]
        self.change_password(user_id)
    
    def change_password(self, user_id=None):
        if not user_id:
            sel = self.tree.selection()
            if not sel:
                messagebox.showerror("Error", "Please select a user")
                return
            user_id = self.tree.item(sel[0])['values'][0]
        
        user_data = self.db.fetch_one("SELECT username, role FROM users WHERE id=?", (user_id,))
        if not user_data:
            return
        
        pop = ctk.CTkToplevel(self)
        pop.title(fix_text("تغيير كلمة المرور"))
        pop.geometry("400x250")
        pop.grab_set()
        
        ctk.CTkLabel(pop, text=fix_text(f"المستخدم: {user_data[0]}"), 
                    font=("Segoe UI", 14, "bold"), text_color="#3498DB").pack(pady=(30, 20))
        
        ctk.CTkLabel(pop, text=fix_text("كلمة المرور الجديدة:"), font=self.AR_FONT).pack(anchor="e", padx=40, pady=(10, 5))
        ent_new_password = ctk.CTkEntry(pop, width=250, show="*", font=self.AR_FONT_NORM)
        ent_new_password.pack(pady=5)
        ent_new_password.focus()
        
        ctk.CTkLabel(pop, text=fix_text("تأكيد كلمة المرور:"), font=self.AR_FONT).pack(anchor="e", padx=40, pady=(15, 5))
        ent_confirm = ctk.CTkEntry(pop, width=250, show="*", font=self.AR_FONT_NORM)
        ent_confirm.pack(pady=5)
        
        def save():
            new_pass = ent_new_password.get().strip()
            confirm_pass = ent_confirm.get().strip()
            
            if not new_pass:
                messagebox.showerror("Error", "Please enter password")
                return
            
            if new_pass != confirm_pass:
                messagebox.showerror("Error", "Passwords do not match")
                return
            
            try:
                # Use Auth Manager to update password
                self.auth.change_password(user_id, new_pass)
                messagebox.showinfo("Success", "Password changed successfully")
                pop.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}")
        
        ctk.CTkButton(pop, text=fix_text("حفظ"), command=save, fg_color="#3498DB", 
                     font=self.AR_FONT, width=250, height=40).pack(pady=30)
        
        ent_confirm.bind("<Return>", lambda e: save())
        ent_new_password.bind("<Return>", lambda e: ent_confirm.focus())
    
    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Please select a user")
            return
        
        user_id = self.tree.item(sel[0])['values'][0]
        username = self.tree.item(sel[0])['values'][1]
        
        if not messagebox.askyesno("Confirm", 
                                   f"Are you sure you want to delete user '{username}'?"):
            return
        
        try:
            self.db.execute("DELETE FROM users WHERE id=?", (user_id,))
            messagebox.showinfo("Success", "User deleted successfully")
            self.load()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")
