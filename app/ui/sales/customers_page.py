
import customtkinter as ctk
from tkinter import ttk, messagebox
from app.database import DB

class CustomersPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.db = DB()
        
        header = ctk.CTkFrame(self, height=50)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="CUSTOMER MANAGER", font=("Arial", 20, "bold")).pack(side="left", padx=20)
        ctk.CTkButton(header, text="+ ADD CUSTOMER", command=self.add_customer, fg_color="#2CC985", width=150, font=("Arial", 12)).pack(side="right", padx=10)
        
        filter_frm = ctk.CTkFrame(self)
        filter_frm.pack(fill="x", padx=10, pady=5)
        self.ent_search = ctk.CTkEntry(filter_frm, placeholder_text="Search Name or Phone...", font=("Arial", 12))
        self.ent_search.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(filter_frm, text="Search", command=self.load, width=100, font=("Arial", 12)).pack(side="left", padx=5)
        
        self.tree = ttk.Treeview(self, columns=("ID", "Name", "Phone", "Address"), show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        for c, w in [("ID", 50), ("Name", 200), ("Phone", 150), ("Address", 300)]:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)
            
        footer = ctk.CTkFrame(self, height=50)
        footer.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(footer, text="EDIT SELECTED", command=self.edit_customer, fg_color="#3B8ED0", font=("Arial", 12)).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(footer, text="DELETE SELECTED", command=self.delete_customer, fg_color="#C0392B", font=("Arial", 12)).pack(side="right", padx=10, pady=10)
        
        self.load()

    def load(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        search = self.ent_search.get().strip()
        sql = "SELECT id, name, phone, address FROM customers WHERE name LIKE ? OR phone LIKE ?"
        param = f"%{search}%"
        for r in self.db.fetch_all(sql, (param, param)):
            self.tree.insert("", "end", values=r)

    def add_customer(self):
        self.open_popup("Add Customer")

    def edit_customer(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showerror("Error", "Select customer first")
        data = self.tree.item(sel[0])['values']
        self.open_popup("Edit Customer", data)

    def open_popup(self, title, data=None):
        pop = ctk.CTkToplevel(self)
        pop.title(title)
        pop.geometry("400x300")
        pop.grab_set()
        
        ctk.CTkLabel(pop, text="Name:", font=("Arial", 12)).pack(pady=5)
        e_name = ctk.CTkEntry(pop, font=("Arial", 12))
        e_name.pack(pady=5)
        
        ctk.CTkLabel(pop, text="Phone:", font=("Arial", 12)).pack(pady=5)
        e_phone = ctk.CTkEntry(pop, font=("Arial", 12))
        e_phone.pack(pady=5)
        
        ctk.CTkLabel(pop, text="Address:", font=("Arial", 12)).pack(pady=5)
        e_addr = ctk.CTkEntry(pop, font=("Arial", 12))
        e_addr.pack(pady=5)
        
        if data:
            e_name.insert(0, data[1])
            e_phone.insert(0, data[2])
            e_addr.insert(0, data[3])
            
        def save():
            n, p, a = e_name.get(), e_phone.get(), e_addr.get()
            if not n: return messagebox.showerror("Error", "Name required")
            if data:
                self.db.execute("UPDATE customers SET name=?, phone=?, address=? WHERE id=?", (n, p, a, data[0]))
            else:
                self.db.execute("INSERT INTO customers (name, phone, address) VALUES (?,?,?)", (n, p, a))
            messagebox.showinfo("Success", "Saved")
            pop.destroy()
            self.load()
            if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
            
        ctk.CTkButton(pop, text="SAVE", command=save, fg_color="#2CC985", font=("Arial", 12)).pack(pady=20)

    def delete_customer(self):
        sel = self.tree.selection()
        if not sel: return
        if messagebox.askyesno("Warning", "Delete customer?"):
            self.db.execute("DELETE FROM customers WHERE id=?", (self.tree.item(sel[0])['values'][0],))
            self.load()
            if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
