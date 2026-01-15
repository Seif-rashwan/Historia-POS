
import customtkinter as ctk
from tkinter import ttk, messagebox
from app.database import DB
from app.utils import fix_text
from .purchase_return_popup import PurchaseReturnPopup

class PurchaseReturnPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.db = DB()
        
        # Title
        ctk.CTkLabel(self, text="إدارة مرتجع المشتريات", font=("Arial", 22, "bold"), text_color="#D35400").pack(pady=10)
        
        # Tab View
        self.tabview = ctk.CTkTabview(self, width=1000, height=600)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # FIX TAB FONT (IMPORTANT FOR ARABIC)
        self.tabview._segmented_button.configure(font=("Arial", 14, "bold"))
        
        self.tab_new = self.tabview.add("تسجيل مرتجع جديد")
        self.tab_history = self.tabview.add("سجل المرتجعات السابقة")
        
        self.setup_new_return_tab()
        self.setup_history_tab()

    # --- TAB 1: NEW RETURN ---
    def setup_new_return_tab(self):
        frm = self.tab_new
        
        # Search
        search_box = ctk.CTkFrame(frm)
        search_box.pack(fill="x", padx=10, pady=5)
        self.ent_search = ctk.CTkEntry(search_box, placeholder_text="ابحث برقم الفاتورة أو اسم المورد...", width=300, font=("Arial", 12))
        self.ent_search.pack(side="left", padx=10, pady=10)
        ctk.CTkButton(search_box, text="بحث", command=self.load_purchases, fg_color="#E67E22", font=("Arial", 12)).pack(side="left", padx=5)
        ctk.CTkButton(search_box, text="فتح نافذة الإرجاع", command=self.open_return_window, fg_color="#27AE60", font=("Arial", 12)).pack(side="right", padx=10)
        
        # Tree
        self.tree = ttk.Treeview(frm, columns=("ID", "Date", "Supplier", "Total", "Payment", "Items"), show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        cols = [("ID", 60), ("Date", 100), ("Supplier", 200), ("Total", 100), ("Payment", 100), ("Items", 80)]
        for c, w in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center")
            
        self.tree.bind("<Double-1>", self.open_return_window)
        self.load_purchases()

    def load_purchases(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        query = self.ent_search.get().strip()
        sql = """
            SELECT p.id, p.date, s.name, p.net_total, p.payment_method, COUNT(d.id) 
            FROM purchases p 
            LEFT JOIN suppliers s ON p.supplier_id = s.id 
            LEFT JOIN purchase_details d ON p.id = d.purchase_id 
            WHERE CAST(p.id AS TEXT) LIKE ? OR s.name LIKE ? 
            GROUP BY p.id ORDER BY p.id DESC
        """
        param = f"%{query}%"
        for r in self.db.fetch_all(sql, (param, param)):
            self.tree.insert("", "end", values=r)

    def open_return_window(self, event=None):
        sel = self.tree.selection()
        if not sel: return messagebox.showerror("Error", "Please select an invoice first.")
        if not sel: return messagebox.showerror("Error", "Please select an invoice first.")
        PurchaseReturnPopup(self, self.tree.item(sel[0])['values'][0], self.controller)
        
    # --- TAB 2: HISTORY ---
    def setup_history_tab(self):
        frm = self.tab_history
        
        ctk.CTkButton(frm, text="تحديث السجل", command=self.load_history, font=("Arial", 12)).pack(pady=5)
        
        self.tree_hist = ttk.Treeview(frm, columns=("Ret_ID", "Date", "Inv_ID", "Supplier", "Items", "Refund", "Notes"), show="headings")
        self.tree_hist.pack(fill="both", expand=True, padx=10, pady=10)
        
        cols = [("Ret_ID", 60), ("Date", 100), ("Inv_ID", 80), ("Supplier", 150), ("Items", 60), ("Refund", 100), ("Notes", 200)]
        for c, w in cols:
            self.tree_hist.heading(c, text=c)
            self.tree_hist.column(c, width=w, anchor="center")
            
        ctk.CTkButton(frm, text="حذف المرتجع المحدد (تراجع)", command=self.delete_return, fg_color="#C0392B", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.load_history()

    def load_history(self):
        for i in self.tree_hist.get_children(): self.tree_hist.delete(i)
        
        # Check if 'purchase_returns' table has 'purchase_id' or 'invoice_id' column
        msg = ""
        try:
             sql = """
                SELECT r.id, r.date, r.purchase_id, s.name, r.qty, r.refund_amount, r.notes 
                FROM purchase_returns r 
                JOIN purchases p ON r.purchase_id = p.id 
                LEFT JOIN suppliers s ON p.supplier_id = s.id 
                ORDER BY r.id DESC
             """
             for r in self.db.fetch_all(sql):
                self.tree_hist.insert("", "end", values=r)
        except Exception as e:
            print(f"Error loading history: {e}")

    def delete_return(self):
        sel = self.tree_hist.selection()
        if not sel: return messagebox.showerror("خطأ", "اختر مرتجعاً للحذف")
        
        if not messagebox.askyesno("تأكيد", "هل أنت متأكد من حذف هذا المرتجع؟\nسيتم إعادة الكميات للمخزن وإلغاء الاسترداد."): return
        
        ret_id = self.tree_hist.item(sel[0])['values'][0]
        # inv_id = self.tree_hist.item(sel[0])['values'][2] 
        # Actually I need the items details.
        # But 'purchase_returns' table doesn't link to details directly? 
        # Wait, PurchaseReturnPopup updated 'purchase_details.returned_qty' and 'store_stock'.
        # But how do we know WHICH items were returned in that specific Return ID?
        # The 'purchase_returns' table only stores summary (qty, amount). It doesn't seem to have a child table 'purchase_return_details'.
        # This implies we CANNOT accurately reverse specific item returns if multiple returns happened on same invoice?
        # OR the original code assumed simple logic.
        # Let's look at the original delete logic in `main.py` lines 2915-2934.
        
        # 2916: item_detail_id, store_id = stock_info (Where did stock_info come from?)
        # It must have fetched it.
        # It seems `purchase_returns` might be 1-to-1 with item? Or simplified?
        # "2920: self.db.execute("UPDATE purchase_details SET returned_qty = returned_qty - ? WHERE id=?", (qty, pd_id))"
        # So it needs `pd_id` (purchase_detail_id).
        # Does `purchase_returns` have `purchase_detail_id`?
        # Or did I miss a JOIN?
        # If the original code works, `purchase_returns` must have `purchase_detail_id` or similar.
        # But my `PurchaseReturnPopup` inserted `(date, purchase_id, qty, amount, notes)`. It did NOT insert detail ID.
        # If `PurchaseReturnPopup` logic in original code was different, I might have broken "Delete Return".
        # Since I synthesized `PurchaseReturnPopup`, I should support what I implemented.
        # My implementation only updates `purchase_details` and `store_stock`. It inserts a summary into `purchase_returns`.
        # So "Delete Return" (Restoring) is impossible accurately if I don't store WHICH items were returned in `purchase_returns`.
        # I should ideally have `purchase_return_details`.
        # BUT, to keep it simple and consistent with "monolithic" approach which might have been simple:
        # If I can't reverse it perfectly, I should disable "Delete Return" or warn.
        # However, the user wants "Extract". I should try to match original functionality.
        # Original:
        # `item_detail_id, store_id = stock_info`
        # This implies it selected stock_info locally.
        # Maybe `purchase_returns` HAS `item_detail_id`?
        # If so, `PurchaseReturnPopup` SHOULD HAVE inserted it.
        # But `PurchaseReturnPopup` handles MULTIPLE items list.
        # Does the original `purchase_returns` store one row per item?
        # If so, `PurchaseReturnPopup` should insert MULTIPLE rows into `purchase_returns`.
        # My `PurchaseReturnPopup` inserted ONE row per TRANSACTION.
        # If the original code inserted ONE row per TRANSACTION, then it couldn't reverse per item.
        # Unless `delete_return` in original code (2915) is looping?
        # I don't see a loop.
        # It seems original code might have been flawed or simplified (one item per return?).
        # Or `purchase_returns` has `purchase_detail_id` column and it logs per item?
        # I will UPDATE `PurchaseReturnPopup` to insert per-item if possible, or leave `delete_return` as "Not Implemented" / "Manual Fix".
        # I'll check `delete_return` (2915) again.
        # `self.db.execute("UPDATE purchase_details ... WHERE id=?", (qty, pd_id))`
        # It uses `pd_id`. `pd_id` must come from the selected row in `tree_hist`.
        # So `tree_hist` must have `pd_id` (purchase detail id).
        # This implies `purchase_returns` table has `purchase_detail_id`.
        # AND `purchase_returns` represents SINGLE ITEM return rows.
        # So `PurchaseReturnPopup` should insert ONE ROW per item returned.
        # My `PurchaseReturnPopup` loop:
        # `for pd_id, qty in items_to_return:`
        #    `UPDATE purchase_details ...`
        #    `UPDATE store_stock ...`
        #    `INSERT INTO purchase_returns ...` <-- THIS SHOULD BE HERE inside loop.
        
        # I will REWRITE `PurchaseReturnPopup` to insert inside loop.
        
        pass

    def delete_return(self):
        sel = self.tree_hist.selection()
        if not sel: return messagebox.showerror("خطأ", "اختر مرتجعاً للحذف")
        
        if not messagebox.askyesno("تأكيد", "هل أنت متأكد من حذف هذا المرتجع؟\nسيتم استعادة الكميات للمخزن."): return
        
        ret_id = self.tree_hist.item(sel[0])['values'][0]
        
        try:
            # Get Store ID from the original purchase
            # Join purchase_returns -> purchases -> stores (or just store_id from purchases)
            res = self.db.fetch_one("""SELECT p.store_id FROM purchase_returns r 
                                      JOIN purchases p ON r.purchase_id = p.id 
                                      WHERE r.id=?""", (ret_id,))
            if not res: return messagebox.showerror("Error", "Available store not found")
            store_id = res[0]
            
            # Get Returned Items details
            # Assuming purchase_return_details exists now
            details = self.db.fetch_all("SELECT purchase_detail_id, qty FROM purchase_return_details WHERE purchase_return_id=?", (ret_id,))
            
            if not details:
                # Fallback for old records (before schema update)
                # If no details found, we can't reverse stock safely.
                # Just delete the record? Or warn?
                # Let's check if it's an old record (qty > 0 but no details)
                # If so, just delete the header.
                self.db.execute("DELETE FROM purchase_returns WHERE id=?", (ret_id,))
                messagebox.showinfo("Success", "Return Invoice Deleted (Old record, no stock reversal applied).")
                self.load_history()
                return

            for pd_id, qty in details:
                # Reverse purchase_details
                self.db.execute("UPDATE purchase_details SET returned_qty = returned_qty - ? WHERE id=?", (qty, pd_id))
                
                # Get item_detail_id
                ires = self.db.fetch_one("SELECT item_detail_id FROM purchase_details WHERE id=?", (pd_id,))
                if ires:
                    did = ires[0]
                    # Add back to Stock
                    # Check if row exists
                    exists = self.db.fetch_one("SELECT 1 FROM store_stock WHERE item_detail_id=? AND store_id=?", (did, store_id))
                    if exists:
                        self.db.execute("UPDATE store_stock SET quantity = quantity + ? WHERE item_detail_id=? AND store_id=?", (qty, did, store_id))
                    else:
                        self.db.execute("INSERT INTO store_stock (item_detail_id, store_id, quantity) VALUES (?,?,?)", (did, store_id, qty))

            self.db.execute("DELETE FROM purchase_return_details WHERE purchase_return_id=?", (ret_id,))
            self.db.execute("DELETE FROM purchase_returns WHERE id=?", (ret_id,))
            
            messagebox.showinfo("Success", "Return Deleted and Stock Restored.")
            self.load_history()
            if hasattr(self.controller, 'refresh_views'): self.controller.refresh_views()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")
