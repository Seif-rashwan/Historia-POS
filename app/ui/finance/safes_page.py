
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import date
from app.database import DB

class SafesPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.db = DB()
        
        # --- Top: Totals & Actions ---
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        # 1. Total Balance Card
        self.card_balance = ctk.CTkFrame(top_frame, height=80, fg_color="#27AE60", corner_radius=10)
        self.card_balance.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkLabel(self.card_balance, text="TOTAL LIQUIDITY", font=("Arial", 12, "bold"), text_color="white").pack(pady=(10,0))
        self.lbl_total_balance = ctk.CTkLabel(self.card_balance, text="$0.00", font=("Arial", 24, "bold"), text_color="white")
        self.lbl_total_balance.pack(pady=5)
        
        # 2. Add Safe Form
        add_frame = ctk.CTkFrame(top_frame, height=80)
        add_frame.pack(side="right", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(add_frame, text="MANAGE SAFES", font=("Arial", 12, "bold")).pack(pady=5)
        input_row = ctk.CTkFrame(add_frame, fg_color="transparent")
        input_row.pack()
        self.ent_new_safe = ctk.CTkEntry(input_row, placeholder_text="New Safe Name...", width=150)
        self.ent_new_safe.pack(side="left", padx=5)
        ctk.CTkButton(input_row, text="+", width=40, command=self.add_safe, fg_color="#2980B9").pack(side="left", padx=2)
        ctk.CTkButton(input_row, text="🗑️", width=40, command=self.delete_safe, fg_color="#C0392B").pack(side="left", padx=2)
        ctk.CTkButton(input_row, text="✏️", width=40, command=self.rename_safe, fg_color="#F39C12").pack(side="left", padx=2)
        
        # Safe Dropdown for selection (to delete/rename)
        self.cb_manage_safe = ctk.CTkComboBox(add_frame, width=200, values=[])
        self.cb_manage_safe.pack(pady=5)

        # --- Middle: Transfer ---
        trans_frame = ctk.CTkFrame(self, fg_color="gray20", corner_radius=10)
        trans_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(trans_frame, text="INTERNAL TRANSFER", font=("Arial", 14, "bold"), text_color="#3498DB").pack(anchor="w", padx=15, pady=10)
        
        row_t = ctk.CTkFrame(trans_frame, fg_color="transparent")
        row_t.pack(fill="x", padx=10, pady=(0, 15))
        
        self.cb_from = ctk.CTkComboBox(row_t, width=160, values=[])
        self.cb_from.pack(side="left", padx=5)
        ctk.CTkLabel(row_t, text="➔", font=("Arial", 16, "bold")).pack(side="left")
        self.cb_to = ctk.CTkComboBox(row_t, width=160, values=[])
        self.cb_to.pack(side="left", padx=5)
        
        self.ent_amount = ctk.CTkEntry(row_t, width=100, placeholder_text="Amount")
        
        # Validation
        self.vcmd = (self.register(self.validate_number), '%P')
        self.ent_amount.configure(validate="key", validatecommand=self.vcmd)
        
        self.ent_amount.pack(side="left", padx=15)
        
        ctk.CTkButton(row_t, text="TRANSFER", command=self.do_transfer, width=100, fg_color="#E67E22").pack(side="left")

        # --- Bottom: Transfer History ---
        ctk.CTkLabel(self, text="Recent Transfers", font=("Arial", 14, "bold")).pack(anchor="w", padx=20)
        self.tree = ttk.Treeview(self, columns=("Date", "From", "To", "Amount"), show="headings", height=8)
        self.tree.pack(fill="both", expand=True, padx=15, pady=5)
        self.tree.heading("Date", text="Date"); self.tree.column("Date", width=100)
        self.tree.heading("From", text="From Safe"); self.tree.column("From", width=150)
        self.tree.heading("To", text="To Safe"); self.tree.column("To", width=150)
        self.tree.heading("Amount", text="Amount"); self.tree.column("Amount", width=100)
        
        self.load_data()

    def validate_number(self, P):
        if P == "": return True
        try:
            float(P)
            return True
        except ValueError:
            return False

    def load_data(self):
        safes = self.db.fetch_all("SELECT id, name FROM safes")
        safe_names = [s[1] for s in safes]
        self.safe_map = {s[1]: s[0] for s in safes} # Name -> ID
        
        self.cb_manage_safe.configure(values=safe_names)
        self.cb_from.configure(values=safe_names)
        self.cb_to.configure(values=safe_names)
        if safe_names:
             self.cb_manage_safe.set(safe_names[0])
             self.cb_from.set(safe_names[0])
             self.cb_to.set(safe_names[1] if len(safe_names)>1 else safe_names[0])
             
        # Calculate Total Balance
        total = 0
        for sid, name in safes:
            # (In +)
            # Vouchers Payment (OUT -), Receipt (IN +)
            # Transfers Out (-), In (+)
            # Invoices (IN +) -- complex if partial payments exist, usually stored in vouchers?
            # Purchases (OUT -) -- stored in vouchers?
            
            # Assuming current architecture:
            # Vouchers table stores EVERYTHING related to money:
            # voucher_type='Payment' (Out), 'Receipt' (In)
            
            # Wait! Transfers are separate table? Yes.
            
            bal = self.get_safe_balance(sid)
            total += bal
            
        self.lbl_total_balance.configure(text=f"EGP{total:,.2f}")
        
        # History
        for i in self.tree.get_children(): self.tree.delete(i)
        sql = """SELECT t.date, s1.name, s2.name, t.amount 
                 FROM transfers t 
                 JOIN safes s1 ON t.from_safe_id = s1.id 
                 JOIN safes s2 ON t.to_safe_id = s2.id 
                 ORDER BY t.id DESC LIMIT 50"""
        for r in self.db.fetch_all(sql):
            self.tree.insert("", "end", values=r)

    def get_safe_balance(self, safe_id):
        # 1. Vouchers
        v_in = self.db.fetch_one("SELECT SUM(amount) FROM vouchers WHERE safe_id=? AND voucher_type='Receipt'", (safe_id,))
        v_in = v_in[0] if v_in and v_in[0] else 0
        
        v_out = self.db.fetch_one("SELECT SUM(amount) FROM vouchers WHERE safe_id=? AND voucher_type='Payment'", (safe_id,))
        v_out = v_out[0] if v_out and v_out[0] else 0
        
        # 2. Transfers
        t_in = self.db.fetch_one("SELECT SUM(amount) FROM transfers WHERE to_safe_id=?", (safe_id,))
        t_in = t_in[0] if t_in and t_in[0] else 0
        
        t_out = self.db.fetch_one("SELECT SUM(amount) FROM transfers WHERE from_safe_id=?", (safe_id,))
        t_out = t_out[0] if t_out and t_out[0] else 0

        # 3. Sales (Invoices) - Cash/Visa IN
        # Only counting what was actually paid (paid_amount)
        # Assuming table columns: net_total or paid_amount? 
        # Checking schema from previous turns: 'paid_amount' was patched in database.py
        s_in = self.db.fetch_one("SELECT SUM(paid_amount) FROM invoices WHERE safe_id=?", (safe_id,))
        s_in = s_in[0] if s_in and s_in[0] else 0

        # 4. Purchases - Money OUT
        # Assuming paid amount is net_total (for now, unless partial payments allowed). 
        # Usually purchases are full payment or tracked. Let's assume net_total for now or check if there is paid_amount.
        # Db schema doesn't show 'paid_amount' for purchases explicitly in my memory, but let's check.
        # Actually, for Purchases, we usually pay full or have 'vouchers' for partial? 
        # If 'Purchases' module inserts a voucher, we double count. 
        # User said: "Purchases (Net Total) (this was missing)". So I will use net_total.
        # But wait, if I create a voucher for a purchase, and also count purchase table, I double count.
        # The user's prompt implies separate tables: "Purchases: money paid to suppliers".
        # I will assume standard purchases DO NOT create vouchers automatically in this system currently, so I count them from Purchases table via safe_id.
        p_out = self.db.fetch_one("SELECT SUM(net_total) FROM purchases WHERE safe_id=?", (safe_id,))
        p_out = p_out[0] if p_out and p_out[0] else 0

        # 5. Sales Returns (Money OUT)
        # Returns table has `refund_amount`. 
        # But wait! In the previous turn (Step 682/683), I ADDED logic to insert a VOUCHER for returns (Payment).
        # "INSERT INTO vouchers ... voucher_type='Payment' ... description='Return/Refund...'"
        # IF I count table `returns` AND `vouchers`, I will Double Count!
        # HOWEVER, the user explicitly asked to include "Sales Returns" in the formula.
        # Maybe I should NOT have added the voucher logic? Or maybe I should specificially exclude Return-Vouchers here?
        # Actually, best practice: if I rely on Vouchers for all manual/misc movements, I should rely on source tables for core business logic if possible.
        # BUT, since I *just* added code to generate Vouchers for returns, counting Returns separately will definitely double count.
        # To avoid confusion and match the User's request (which lists them separately), I should probably REMOVE the voucher generation from ReturnsPage OR filter them out here.
        # GIVEN the user's specific request "The formula should be: ... Vouchers ... Sales Returns", it implies they want to sum the `returns` table.
        # So, I should probably rely on the transaction tables.
        # I will subtract Sales Returns (from returns table). 
        # Note: If I keep my previous change (generating vouchers), I must fix it. 
        # I will assume for this step I am implementing the User's formula.
        # IMPORTANT: I need to be careful about Double Counting if vouchers exist for these.
        # Verification: Does `save_invoice` create a voucher? No.
        # Does `save_purchase` create a voucher? No.
        # Does `save_return` create a voucher? YES (I added it).
        # Does `PurchaseReturn` create a voucher? No (I didn't add it there, I think).
        
        # DECISION: I will calculate from the core tables as requested. 
        # `vouchers` should be for PURE manual entries (Expenses, Capital).
        # If I have auto-generated vouchers, they pollute this if I sum both.
        # I will use the query to exclude auto-generated vouchers? Or assume the user wants me to use the core tables implies I should maybe revert the voucher-generation or ignore it.
        # Safest bet: Sum `vouchers` where description NOT LIKE 'Return%'? No that's brittle.
        # Use simple Sums as requested.
        
        sr_out = self.db.fetch_one("SELECT SUM(refund_amount) FROM returns WHERE invoice_id IN (SELECT id FROM invoices WHERE safe_id=?)", (safe_id,))
        # Wait, returns don't have safe_id? I didn't add it to schema.
        # ReturnPopup Logic I added: "Refund From Safe" -> Insert into VOUCHERS.
        # It did NOT update `returns` table with `safe_id`.
        # So I CANNOT sum `returns` by safe_id directly unless I join/assume.
        # User said "Sales Returns: money returned to customer".
        # If I can't filter returns by safe, I can't calculate per safe.
        # BUT, I *did* insert a Voucher for it. So `v_out` ALREADY includes it.
        # If I add `sr_out`, I double count.
        # User says: "Your code is missing... Sales Returns".
        # This implies the user *thinks* I am not capturing it.
        # If I say "Bro, I added vouchers for it", he might say "No, use the table".
        # But the table doesn't have Safe ID.
        # So I MUST rely on the Voucher for Sales Returns (since I implemented it that way).
        # OR I should update `returns` schema to have `safe_id`.
        
        # Let's look at `Sales` (Invoices). Does it have safe_id? Yes, schema has `safe_id`.
        # So `s_in` works.
        
        # Purchases? `purchases` table has `safe_id`.
        # So `p_out` works.
        
        # Purchase Returns? `purchase_returns` table... check schema.
        # `purchase_returns` table schema (step 679): id, date, purchase_id, qty, refund_amount, notes.
        # NO safe_id.
        # So, Purchase Returns also pose a "Which safe?" problem.
        
        # CONCLUSION:
        # The user's provided formula is the "Theoretical Correct Formula".
        # In practice, `vouchers` table is often used as the "General Ledger" for cash.
        # If we didn't use Vouchers for Returns, we'd be stuck.
        
        # However, for `Sales` and `Purchases`, we definitely DO NOT have vouchers. 
        # So I MUST add those queries.
        
        # Strategies:
        # 1. Add `s_in` (Sales) and `p_out` (Purchases).
        # 2. For Returns: Since `v_out` (Vouchers) tracks the return I implemented, I don't need to add `sr_out`.
        #    BUT the user explicitly said "Sales Returns" is missing.
        #    Maybe I should verify if `save_order` creates a voucher? (I reviewed it, it doesn't).
        #    So `s_in` is definitely needed.
        #    `p_out` is definitely needed.
        
        #    What about Returns? 
        #    If I use `v_out`, I cover the returns I fixed.
        #    If I add `sr_out` I double count.
        #    I'll assume the user wants me to use the tables solely? No, vouchers are needed for expenses.
        
        #    I will add Sales and Purchases.
        #    I will COMMENT about Returns being covered by Vouchers (or I will filter them).
        #    Actually, `Purchase Returns` (Refund from supplier) -> Money IN.
        #    I have NOT added logic to create vouchers for Purchase Returns.
        #    So I NEED `pr_in`.
        #    But `purchase_returns` lacks `safe_id`.
        #    I will assume it goes back to the safe of the original purchase?
        #    Query: JOIN purchase_returns -> purchases -> safe_id.
        
        #    For `Sales Returns` (Money OUT):
        #    I DID add logic to create vouchers.
        #    If I want to follow the User's formula strictly, I should stop creating vouchers for returns and use the table.
        #    BUT `returns` table lacks `safe_id`.
        #    Currently my Voucher logic handles the "Which safe" selection properly.
        #    So VOUCHERS is the correct place for Sales Returns in my current implementation.
        
        #    So, my update will be:
        #    Balance = (Vouchers_In + Transfers_In + Sales_Paid + Purchase_Returns_Linked) 
        #            - (Vouchers_Out + Transfers_Out + Purchases_Net)
        
        #    *Wait, Purchase Returns Linked?*
        #    SELECT SUM(pr.refund_amount) FROM purchase_returns pr JOIN purchases p ON pr.purchase_id=p.id WHERE p.safe_id=?
        
        #    *Sales Returns?*
        #    If I count them via Vouchers, I am good.
        #    I will NOT add a separate query for Sales Returns to avoid double counting, unless I filter the vouchers.
        #    Actually, to be safe and clean, I should count them from the Vouchers (as they are payments).
        #    I will stick to adding Sales and Purchases and Purchase Returns.
        
        #    Let's refine the Purchase Returns query:
        #    `SELECT SUM(refund_amount) FROM purchase_returns JOIN purchases ON ...`
        
        #    And Sales:
        #    `SELECT SUM(paid_amount) FROM invoices WHERE safe_id=?`
        
        #    And Purchases:
        #    `SELECT SUM(net_total) FROM purchases WHERE safe_id=?`
        
        pr_in = self.db.fetch_one("SELECT SUM(pr.refund_amount) FROM purchase_returns pr JOIN purchases p ON pr.purchase_id = p.id WHERE p.safe_id=?", (safe_id,))
        pr_in = pr_in[0] if pr_in and pr_in[0] else 0

        # Purchase Returns = Money IN (Refund from supplier)
        
        # Final Sum:
        # IN = v_in + t_in + s_in + pr_in
        # OUT = v_out + t_out + p_out
        
        # Note: Sales Returns are entered as Vouchers (Payment) in my previous fix, so they are inside `v_out`.
        
        return (v_in + t_in + s_in + pr_in) - (v_out + t_out + p_out)

    def add_safe(self):
        name = self.ent_new_safe.get().strip()
        if not name: return
        self.db.execute("INSERT INTO safes (name) VALUES (?)", (name,))
        self.ent_new_safe.delete(0, "end")
        messagebox.showinfo("Success", "Safe Added")
        self.load_data()
        if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()

    def delete_safe(self):
        name = self.cb_manage_safe.get()
        if not name or name not in self.safe_map: return
        sid = self.safe_map[name]
        
        # Checks
        if self.db.fetch_one("SELECT 1 FROM vouchers WHERE safe_id=?", (sid,)):
            return messagebox.showerror("Error", "Cannot delete: Safe has vouchers.")
        if self.db.fetch_one("SELECT 1 FROM transfers WHERE from_safe_id=? OR to_safe_id=?", (sid, sid)):
            return messagebox.showerror("Error", "Cannot delete: Safe has transfers.")
        if self.db.fetch_one("SELECT 1 FROM invoices WHERE safe_id=?", (sid,)):
             return messagebox.showerror("Error", "Cannot delete: Safe linked to invoices.")
             
        if messagebox.askyesno("Confirm", f"Delete Safe '{name}'?"):
            self.db.execute("DELETE FROM safes WHERE id=?", (sid,))
            messagebox.showinfo("Success", "Deleted")
            self.load_data()
            if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()

    def rename_safe(self):
        name = self.cb_manage_safe.get()
        new_name = self.ent_new_safe.get().strip()
        if not name or not new_name: return messagebox.showerror("Error", "Select safe and enter new name")
        sid = self.safe_map[name]
        
        self.db.execute("UPDATE safes SET name=? WHERE id=?", (new_name, sid))
        self.ent_new_safe.delete(0, "end")
        messagebox.showinfo("Success", "Renamed")
        self.load_data()
        if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()

    def do_transfer(self):
        f, t = self.cb_from.get(), self.cb_to.get()
        try: amount = float(self.ent_amount.get())
        except: return messagebox.showerror("Error", "Invalid Amount")
        
        if f == t: return messagebox.showerror("Error", "Select different safes")
        if amount <= 0: return messagebox.showerror("Error", "Amount must be positive")
        
        sid_f, sid_t = self.safe_map[f], self.safe_map[t]
        
        # Check Balance
        bal = self.get_safe_balance(sid_f)
        if bal < amount:
            return messagebox.showerror("Error", f"Insufficient Funds in {f} (Bal: {bal:,.2f})")
            
        self.db.execute("INSERT INTO transfers (date, from_safe_id, to_safe_id, amount) VALUES (?,?,?,?)",
                       (date.today(), sid_f, sid_t, amount))
                       
        messagebox.showinfo("Success", "Transferred")
        self.ent_amount.delete(0, "end")
        self.load_data()
        if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
