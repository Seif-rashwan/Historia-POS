import customtkinter as ctk
from tkinter import messagebox
from app.utils import fix_text
from app.database import DB
from app.auth import LoginManager

class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, on_login_success):
        super().__init__(parent)
        self.on_login_success = on_login_success
        self.current_user_role = None
        self.auth = LoginManager()
        
        # Configure to fill parent
        self.pack(fill="both", expand=True)
        
        # Frame (Container)
        frame = ctk.CTkFrame(self, fg_color="gray20")
        frame.pack(expand=True, padx=20, pady=20)
        
        # Title
        ctk.CTkLabel(frame, text=fix_text("تسجيل الدخول"), font=("Segoe UI", 24, "bold")).pack(pady=(30, 20))
        
        # --- Username Section ---
        # جعلنا anchor="e" ليكون في اليمين، وضبطنا padx ليكون محاذياً للخانة
        ctk.CTkLabel(frame, text=fix_text("اسم المستخدم:"), font=("Segoe UI", 14)).pack(anchor="e", padx=45, pady=(10, 5))
        
        # أضفنا justify="right" للكتابة من اليمين
        self.ent_username = ctk.CTkEntry(frame, width=250, font=("Segoe UI", 14), 
                                         justify="right", 
                                         placeholder_text=fix_text("أدخل اسم المستخدم"))
        self.ent_username.pack(pady=5, padx=20)
        self.ent_username.bind("<Return>", lambda e: self.ent_password.focus())
        
        # --- Password Section ---
        ctk.CTkLabel(frame, text=fix_text("كلمة المرور:"), font=("Segoe UI", 14)).pack(anchor="e", padx=45, pady=(15, 5))
        
        # أضفنا justify="right" للكتابة من اليمين
        self.ent_password = ctk.CTkEntry(frame, width=250, show="*", font=("Segoe UI", 14), 
                                         justify="right",
                                         placeholder_text=fix_text("أدخل كلمة المرور"))
        self.ent_password.pack(pady=5, padx=20)
        self.ent_password.bind("<Return>", lambda e: self.login())
        
        # Login Button
        btn_login = ctk.CTkButton(frame, text=fix_text("دخول"), command=self.login, 
                                 fg_color="#27AE60", font=("Segoe UI", 16, "bold"), width=250, height=40)
        btn_login.pack(pady=30, padx=20)
        
        # Default credentials hint
        ctk.CTkLabel(frame, text=fix_text("افتراضي: admin/123 أو sales/123"), 
                    font=("Segoe UI", 10), text_color="gray70").pack(pady=5)
        
        self.ent_username.focus()
    
    def login(self):
        username = self.ent_username.get().strip()
        password = self.ent_password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return
        
        # Use LoginManager
        role = self.auth.login(username, password)
        
        if role:
            self.current_user_role = role
            # Call the callback to transition to main app
            self.on_login_success(self.current_user_role)
        else:
            messagebox.showerror("Error", "Incorrect username or password")