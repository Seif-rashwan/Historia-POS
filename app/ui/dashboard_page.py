import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
from datetime import date, timedelta
from app.database import DB
from app.utils import fix_text, MATPLOTLIB_AVAILABLE
from app.ui.inventory.store_details_popup import StoreDetailsPopup

if MATPLOTLIB_AVAILABLE:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class DashboardPage(ctk.CTkScrollableFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.db = DB()
        
        # Configure grid expansion for the scrollable content
        self.grid_columnconfigure(0, weight=1)
        self.load()

    def load(self):
        # Clear existing content
        for widget in self.winfo_children():
            widget.destroy()

        # --- 1. STATISTICS (Cards) ---
        try:
            i_count = self.db.fetch_one("SELECT COUNT(*) FROM items")[0]
            q_count = self.db.fetch_one("SELECT SUM(quantity) FROM store_stock")[0] or 0
            v_count = self.db.fetch_one("SELECT SUM(ss.quantity * d.buy_price) FROM store_stock ss JOIN item_details d ON ss.item_detail_id=d.id")[0] or 0
            
            # Calculate Estimated Net Profit (All Time)
            total_sales = self.db.fetch_one("SELECT SUM(net_total) FROM invoices")[0] or 0
            total_exp = self.db.fetch_one("SELECT SUM(amount) FROM vouchers WHERE voucher_type='Payment'")[0] or 0
            total_ret = self.db.fetch_one("SELECT SUM(refund_amount) FROM returns")[0] or 0
            
            # COGS - FIXED: Use cost_at_sale (historical cost) instead of current buy_price
            total_cogs = self.db.fetch_one("""
                SELECT SUM(id.qty * id.cost_at_sale) 
                FROM invoice_details id
            """)[0] or 0
            
            est_net_profit = total_sales - total_ret - total_cogs - total_exp
            
            # Title Header Frame
            header_frame = ctk.CTkFrame(self, fg_color="transparent")
            header_frame.pack(fill="x", pady=(20, 10), padx=30)
            
            ctk.CTkLabel(header_frame, text=fix_text("نظرة عامة (Overview)"), font=("Segoe UI", 26, "bold")).pack(side="right")
            
            # Manual Backup Button
            ctk.CTkButton(header_frame, text=fix_text("💾 Backup Database manually"), command=self.manual_backup,
                          fg_color="#27AE60", hover_color="#2ECC71", font=("Arial", 12, "bold"), width=120).pack(side="left")
            
            # Cards Container
            f = ctk.CTkFrame(self, fg_color="transparent")
            f.pack(fill="x", padx=20)
            
            stats = [
                (fix_text("الأصناف"), i_count, "#3B8ED0"), 
                (fix_text("صافي الربح (تقريبي)"), f"{est_net_profit:,.0f}", "#27AE60" if est_net_profit >= 0 else "#C0392B"),
                (fix_text("قيمة المخزون"), f"{v_count:,.0f}", "#E67E22"),
                (fix_text("إجمالي المبيعات"), f"{total_sales:,.0f}", "#8E44AD")
            ]
            
            for idx, (t, val, col) in enumerate(stats):
                c = ctk.CTkFrame(f, height=120, fg_color="gray20", border_width=0, corner_radius=10)
                c.grid(row=0, column=idx, sticky="ew", padx=10)
                f.grid_columnconfigure(idx, weight=1)
                
                ctk.CTkLabel(c, text=t, text_color="gray80", font=("Segoe UI", 14, "bold")).pack(pady=(20,5), anchor="e", padx=15)
                ctk.CTkLabel(c, text=str(val), font=("Arial", 24, "bold"), text_color=col).pack(pady=(0,20), anchor="e", padx=15)

            # --- 2. CHARTS SECTION ---
            if MATPLOTLIB_AVAILABLE:
                charts_frame = ctk.CTkFrame(self, fg_color="transparent")
                charts_frame.pack(fill="x", padx=20, pady=20)
                
                # Chart 1: Sales Last 7 Days
                self.create_chart_frame(charts_frame, 0, 0, fix_text("المبيعات (آخر 7 أيام)"), self.plot_sales_7_days)
                
                # Chart 2: Top 5 Selling Items
                self.create_chart_frame(charts_frame, 0, 1, fix_text("الأكثر مبيعاً (Top 5)"), self.plot_top_items)
                
                charts_frame.grid_columnconfigure(0, weight=1)
                charts_frame.grid_columnconfigure(1, weight=1)
                
                # Chart 3 & 4 Row
                charts_row2 = ctk.CTkFrame(self, fg_color="transparent")
                charts_row2.pack(fill="x", padx=20, pady=0)
                
                # Chart 3: Income vs Expenses
                self.create_chart_frame(charts_row2, 0, 0, fix_text("المصروفات vs المبيعات"), lambda ax: self.plot_income_vs_expense(ax, total_sales, total_exp))
                
                # Chart 4: Payment Methods
                self.create_chart_frame(charts_row2, 0, 1, fix_text("طرق الدفع (آخر 30 يوم)"), self.plot_payment_methods)

                charts_row2.grid_columnconfigure(0, weight=1)
                charts_row2.grid_columnconfigure(1, weight=1)

            # --- 3. TREASURY (Safes) ---
            ctk.CTkLabel(self, text=fix_text("مراقبة الخزائن"), font=("Segoe UI", 22, "bold")).pack(pady=(30,10), anchor="e", padx=30)
            t_frame = ctk.CTkFrame(self, fg_color="transparent")
            t_frame.pack(fill="x", padx=20, pady=(0,20))
            
            safes = self.db.fetch_all("SELECT id, name FROM safes")
            for idx, (sid, name) in enumerate(safes):
                name_fixed = fix_text(name)
                inc = self.db.fetch_one("SELECT SUM(paid_amount) FROM invoices WHERE safe_id=?", (sid,))[0] or 0
                v_in = self.db.fetch_one("SELECT SUM(amount) FROM vouchers WHERE safe_id=? AND voucher_type='Receipt'", (sid,))[0] or 0
                tin = self.db.fetch_one("SELECT SUM(amount) FROM transfers WHERE to_safe_id=?", (sid,))[0] or 0
                ret = self.db.fetch_one("SELECT SUM(r.refund_amount) FROM returns r JOIN invoices i ON r.invoice_id=i.id WHERE i.safe_id=?", (sid,))[0] or 0
                pur = self.db.fetch_one("SELECT SUM(net_total) FROM purchases WHERE safe_id=?", (sid,))[0] or 0
                v_out = self.db.fetch_one("SELECT SUM(amount) FROM vouchers WHERE safe_id=? AND voucher_type='Payment'", (sid,))[0] or 0
                tout = self.db.fetch_one("SELECT SUM(amount) FROM transfers WHERE from_safe_id=?", (sid,))[0] or 0
                
                # FIX: Add purchase returns (money returned from suppliers)
                pur_ret = self.db.fetch_one("SELECT SUM(pr.refund_amount) FROM purchase_returns pr JOIN purchases p ON pr.purchase_id=p.id WHERE p.safe_id=?", (sid,))[0] or 0
                
                # Updated formula: includes purchase returns as incoming cash
                balance = (inc + v_in + tin + pur_ret) - (ret + pur + v_out + tout)
                
                c = ctk.CTkFrame(t_frame, height=100, fg_color="#2C3E50", corner_radius=10)
                c.grid(row=idx//3, column=idx%3, sticky="ew", padx=10, pady=5)
                t_frame.grid_columnconfigure(idx%3, weight=1)
                
                ctk.CTkLabel(c, text=name_fixed, font=("Segoe UI", 13, "bold"), text_color="white").pack(pady=(15,5), anchor="e", padx=10)
                ctk.CTkLabel(c, text=f"{balance:,.2f}", font=("Arial", 18, "bold"), text_color="#F1C40F").pack(pady=(0,15), anchor="e", padx=10)
                
            # --- 4. STORE DETAILS ---
            ctk.CTkLabel(self, text=fix_text("تفاصيل المخازن"), font=("Segoe UI", 22, "bold")).pack(pady=(30,10), anchor="e", padx=30)
            sf = ctk.CTkFrame(self, fg_color="transparent")
            sf.pack(fill="x", padx=20, pady=(0, 20))
            
            store_stats = self.db.fetch_all("""SELECT s.id, s.name, IFNULL(SUM(ss.quantity), 0) FROM stores s LEFT JOIN store_stock ss ON s.id=ss.store_id GROUP BY s.id""")
            
            for idx, (sid, n, q) in enumerate(store_stats):
                btn = ctk.CTkButton(sf, text=f"{fix_text(n)}\n{int(q)} Items", height=80, 
                                    fg_color="gray25", border_width=1, border_color="gray40", 
                                    font=("Segoe UI", 16, "bold"), 
                                    command=lambda s=sid, nm=n: StoreDetailsPopup(self, s, nm))
                btn.grid(row=idx//2, column=idx%2, sticky="ew", padx=10, pady=10)
                
            sf.grid_columnconfigure(0, weight=1)
            sf.grid_columnconfigure(1, weight=1)
                
        except Exception as e:
            ctk.CTkLabel(self, text=f"Error loading dashboard: {e}", text_color="red").pack()

    def create_chart_frame(self, parent, row, col, title, plot_func):
        c = ctk.CTkFrame(parent, fg_color="gray20", corner_radius=10)
        c.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(c, text=title, font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        fig, ax = plt.subplots(figsize=(4.5, 3.2), facecolor='#2b2b2b')
        ax.set_facecolor('#2b2b2b')
        ax.tick_params(colors='white', labelsize=8)
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plot_func(ax)
        
        canvas = FigureCanvasTkAgg(fig, c)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=10, pady=10, fill="both", expand=True)
        plt.close(fig)

    def plot_sales_7_days(self, ax):
        dates_list = [(date.today() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
        sales_data = self.db.fetch_all("""SELECT date, SUM(net_total) FROM invoices WHERE date >= date('now', '-7 days') GROUP BY date""")
        sales_dict = {row[0]: row[1] for row in sales_data}
        final_sales = [sales_dict.get(d, 0) for d in dates_list]
        short_dates = [d[5:] for d in dates_list]
        ax.bar(short_dates, final_sales, color='#3498DB', alpha=0.8)

    def plot_top_items(self, ax):
        top_items = self.db.fetch_all("""
            SELECT i.name, SUM(id.qty) as total_qty
            FROM invoice_details id
            JOIN item_details d ON id.item_detail_id = d.id
            JOIN items i ON d.item_id = i.id
            JOIN invoices inv ON id.invoice_id = inv.id
            WHERE inv.date >= date('now', '-30 days')
            GROUP BY i.name
            ORDER BY total_qty DESC
            LIMIT 5
        """)
        if top_items:
            i_names = [fix_text(row[0]) for row in top_items]
            i_qtys = [row[1] for row in top_items]
            ax.barh(i_names, i_qtys, color='#E67E22', alpha=0.8)
            ax.invert_yaxis()
        else:
            ax.text(0.5, 0.5, "No Data", ha='center', va='center', color='gray')

    def plot_income_vs_expense(self, ax, total_sales, total_exp):
        income_receipts = self.db.fetch_one("SELECT SUM(amount) FROM vouchers WHERE voucher_type='Receipt'")[0] or 0
        total_income = total_sales + income_receipts
        total_purchases = self.db.fetch_one("SELECT SUM(net_total) FROM purchases")[0] or 0
        total_out = total_purchases + total_exp
        
        labels = [fix_text('دخل (Income)'), fix_text('مصروفات (Exp)')]
        sizes = [total_income, total_out]
        colors = ['#27AE60', '#C0392B']
        if sum(sizes) > 0:
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors, textprops={'color':"w"})
        else:
             ax.text(0.5, 0.5, "No Data", ha='center', va='center', color='gray')

    def plot_payment_methods(self, ax):
        pay_data = self.db.fetch_all("""SELECT payment_method, SUM(net_total) FROM invoices WHERE date >= date('now', '-30 days') GROUP BY payment_method""")
        if pay_data:
            lbls = [fix_text(r[0] or "?") for r in pay_data]
            vals = [r[1] for r in pay_data]
            ax.pie(vals, labels=lbls, autopct='%1.1f%%', textprops={'color':"w"})
        else:
            ax.text(0.5, 0.5, "No Data", ha='center', va='center', color='gray')

    def manual_backup(self):
        try:
            self.db.backup_database()
            # Get latest backup file
            import glob, os
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            backup_dir = os.path.join(base_dir, "backups")
            list_of_files = glob.glob(os.path.join(backup_dir, "*.db"))
            if list_of_files:
                latest_file = max(list_of_files, key=os.path.getmtime)
                messagebox.showinfo("Backup Success", f"Backup created successfully!\n\nLocation:\n{latest_file}")
            else:
                 messagebox.showinfo("Backup Success", "Backup created successfully in backups/ folder.")
        except Exception as e:
            messagebox.showerror("Backup Error", f"An error occurred: {e}")
