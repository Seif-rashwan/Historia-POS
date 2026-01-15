
import customtkinter as ctk
from .login_page import LoginPage
from tkinter import filedialog, messagebox
from app.config_manager import ConfigManager
from app.utils import fix_text
from app.config import ASSETS_DIR
from app.config import ICON_PATH

# Import all Pages
from .sales.order_page import OrderPage
from .sales.customers_page import CustomersPage
from .sales.history_page import HistoryPage
from .sales.returns_page import ReturnsPage
from .sales.invoice_viewer import InvoiceViewer

from .inventory.stock_page import StockPage
from .inventory.transfer_page import TransferPage
from .inventory.suppliers_page import SuppliersPage
from .inventory.import_data_page import ImportDataPage

from .finance.vouchers_page import VouchersPage
from .finance.safes_page import SafesPage
from .finance.pending_page import PendingPage
from .finance.reports_page import ReportsPage

from .purchases.purchase_invoice_page import PurchaseInvoicePage
from .purchases.purchase_return_page import PurchaseReturnPage

from .users_page import UsersPage
from .dashboard_page import DashboardPage
from .purchases.purchase_history_page import PurchaseHistoryPage

class InventoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(fix_text("HISTORIA"))
        self.geometry("400x350")
        
        # Icon
        try:
            self.iconbitmap(ICON_PATH)
        except: pass

        # Center window
        self.center_window(400, 350)
        
        self.user_role = None
        
        # Page References for Auto-Refresh
        self.customers_page = None
        self.suppliers_page = None
        self.history_page = None
        self.stock_page = None
        self.safes_page = None
        self.pending_page = None
        self.purchase_history_page = None
        self.dashboard_page = None
        self.purchase_return_page = None
        self.sales_return_page = None
        
        self.show_login()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        try:
            from app.database import DB
            db = DB()
            print("💾 Creating Auto-Backup before exit...")
            db.backup_database()
        except Exception as e:
            print(f"Backup Error: {e}")
        finally:
            self.destroy()

    def center_window(self, w, h):
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def show_login(self):
        self.login_frame = LoginPage(self, self.on_login_success)
        self.login_frame.pack(fill="both", expand=True)

    def on_login_success(self, user_role):
        self.user_role = user_role
        self.login_frame.destroy()
        
        # Configure for Main App
        self.title(fix_text("HISTORIA"))
        w, h = 1400, 850
        self.geometry(f"{w}x{h}")
        self.center_window(w, h)
        self.minsize(1024, 768)
        
        self.setup_ui()

    def setup_ui(self):
        # Main Layout: Sidebar + Content
        self.grid_columnconfigure(0, weight=1)  # Content Area Weight (Left)
        # self.grid_columnconfigure(1, weight=0) # Sidebar (Right - Automatic width)
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=1, sticky="nsew") # Sidebar on Right
        self.sidebar.grid_rowconfigure(10, weight=1) # Spacer
        
        self.content_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_area.grid(row=0, column=0, sticky="nsew") # Content on Left
        
        # Sidebar Buttons
        # HISTORIA Logo/Refresh Button
        logo_btn = ctk.CTkButton(
            self.sidebar, 
            text="HISTORIA", 
            font=("Arial", 24, "bold"), 
            text_color="#3498DB",
            fg_color="transparent",
            hover_color=("gray90", "gray20"),
            command=self.reset_current_page,
            cursor="hand2"
        )
        logo_btn.pack(pady=30)
        
        self.nav_buttons = {}
        
        nav_items = [
            ("dashboard", "الرئيسية"),
            ("sales", "نقطة البيع"),
            ("inventory", "المخزون"),
            ("finance", "المالية"),
            ("purchases", "المشتريات"),
            ("analysis", "التقارير")
        ]
        
        if self.user_role == "Admin":
            nav_items.append(("users", "المستخدمين"))

        for key, label in nav_items:
            btn = ctk.CTkButton(self.sidebar, text=fix_text(label), command=lambda k=key: self.show_page(k), 
                                font=("Arial", 14, "bold"), fg_color="transparent", text_color=("gray10", "gray90"), 
                                hover_color=("gray70", "gray30"), height=40, anchor="w")
            btn.pack(fill="x", padx=10, pady=5)
            self.nav_buttons[key] = btn
            
        # Change Folder Button
        ctk.CTkButton(self.sidebar, text=fix_text("مجلد الفواتير"), command=self.change_save_folder,
                      fg_color="transparent", border_width=1, border_color="gray50", font=("Arial", 12)).pack(side="bottom", pady=(10, 10), padx=20, fill="x")
            
        # Logout
        ctk.CTkButton(self.sidebar, text=fix_text("تسجيل خروج"), command=self.logout, 
                      fg_color="#C0392B", font=("Arial", 12, "bold")).pack(side="bottom", pady=20, padx=20, fill="x")

        # Create Pages Container
        self.pages = {}
        self.current_page = None
        
        # Default Page
        self.show_page("dashboard")

    def show_page(self, page_key):
        # Update sidebar highlighting
        for k, btn in self.nav_buttons.items():
            if k == page_key:
                btn.configure(fg_color=("gray75", "gray25"), text_color="#3498DB")
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))

        # Clear Content
        if self.current_page:
            self.current_page.pack_forget()
            
        # Check if page exists, else create it
        if page_key not in self.pages:
            self.pages[page_key] = self.create_page(page_key)
            
        self.current_page = self.pages[page_key]
        self.current_page.pack(fill="both", expand=True)

    def create_page(self, key):
        # Special case for Dashboard: No TabView, direct instantiation
        if key == "dashboard":
            self.dashboard_page = DashboardPage(self.content_area, controller=self)
            return self.dashboard_page

        # For strict layouts, we use a container frame
        frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        
        # Use TabView for sections within main categories
        tabs = ctk.CTkTabview(frame)
        tabs.pack(fill="both", expand=True)
        tabs._segmented_button.configure(font=("Arial", 12, "bold"))
        
        if key == "sales":
            tabs.add("فاتورة جديدة")
            tabs.add("العملاء")
            tabs.add("أرشيف الفواتير")
            tabs.add("المرتجعات")
            
            OrderPage(tabs.tab("فاتورة جديدة"), self).pack(fill="both", expand=True)
            
            self.customers_page = CustomersPage(tabs.tab("العملاء"))
            self.customers_page.pack(fill="both", expand=True)
            
            self.history_page = HistoryPage(tabs.tab("أرشيف الفواتير"), controller=self)
            self.history_page.pack(fill="both", expand=True)
            
            self.sales_return_page = ReturnsPage(tabs.tab("المرتجعات"), controller=self)
            self.sales_return_page.pack(fill="both", expand=True)
            
        elif key == "inventory":
            tabs.add("المخزون")
            tabs.add("التحويلات")
            tabs.add("الموردين")
            
            self.stock_page = StockPage(tabs.tab("المخزون"), user_role=self.user_role, controller=self)
            self.stock_page.pack(fill="both", expand=True)
            
            TransferPage(tabs.tab("التحويلات"), controller=self).pack(fill="both", expand=True)
            
            self.suppliers_page = SuppliersPage(tabs.tab("الموردين"), controller=self)
            self.suppliers_page.pack(fill="both", expand=True)
            
            if self.user_role == "Admin":
                tabs.add("استيراد بيانات")
                ImportDataPage(tabs.tab("استيراد بيانات"), self).pack(fill="both", expand=True)
                
        elif key == "finance":
            tabs.add("الخزائن")
            tabs.add("السندات")
            tabs.add("الفواتير الآجلة")
            
            self.safes_page = SafesPage(tabs.tab("الخزائن"), controller=self)
            self.safes_page.pack(fill="both", expand=True)
            
            VouchersPage(tabs.tab("السندات"), controller=self).pack(fill="both", expand=True)
            
            self.pending_page = PendingPage(tabs.tab("الفواتير الآجلة"), controller=self)
            self.pending_page.pack(fill="both", expand=True)
            
        elif key == "purchases":
            tabs.add("فاتورة مشتريات")
            tabs.add("مرتجع مشتريات")
            tabs.add("أرشيف المشتريات")
            
            PurchaseInvoicePage(tabs.tab("فاتورة مشتريات"), controller=self).pack(fill="both", expand=True)
            
            self.purchase_return_page = PurchaseReturnPage(tabs.tab("مرتجع مشتريات"), controller=self)
            self.purchase_return_page.pack(fill="both", expand=True)
            
            self.purchase_history_page = PurchaseHistoryPage(tabs.tab("أرشيف المشتريات"), self)
            self.purchase_history_page.pack(fill="both", expand=True)
            
        elif key == "analysis":
            tabs.add("التقارير")
            ReportsPage(tabs.tab("التقارير"), user_role=self.user_role).pack(fill="both", expand=True)
            
        elif key == "users":
            tabs.add("إدارة المستخدمين")
            UsersPage(tabs.tab("إدارة المستخدمين"), controller=self).pack(fill="both", expand=True)

        return frame

    def logout(self):
        self.destroy()
    
    def edit_old_invoice(self, invoice_id):
        self.show_page("sales")
        sales_frame = self.pages.get("sales")
        # Navigate to OrderPage within Tabs
        tabview = None
        for child in sales_frame.winfo_children():
            if isinstance(child, ctk.CTkTabview):
                tabview = child
                break
        
        if tabview:
            tabview.set("فاتورة جديدة")
            tab_frame = tabview.tab("فاتورة جديدة")
            for child in tab_frame.winfo_children():
                if isinstance(child, OrderPage):
                    child.load_for_edit(invoice_id)
                    break 

    def show_dashboard(self):
        self.refresh_views()
        self.show_page("dashboard")
        
    def refresh_views(self):
        """Refreshes data in all stored page references"""
        pages_to_refresh = [
            (self.dashboard_page, 'load'),
            (self.customers_page, 'load'),
            (self.history_page, 'load'),
            (self.stock_page, 'load'),
            (self.suppliers_page, 'load'),
            (self.safes_page, 'load_data'),
            (self.pending_page, 'load_invoices'),
            (self.purchase_history_page, 'load'),
            (self.sales_return_page, 'load'),
            (self.purchase_return_page, 'load_purchases')
        ]
        
        for page, method_name in pages_to_refresh:
            if page and hasattr(page, method_name):
                try:
                    getattr(page, method_name)()
                except Exception as e:
                    print(f"Error refreshing {page}: {e}")

    def reset_current_page(self):
        """
        Resets the currently active page - clears forms, carts, and starts fresh.
        Works across all pages (invoices, purchases, returns, etc.)
        """
        if not self.current_page:
            return
        
        try:
            # For pages with TabView (sales, purchases, inventory, finance)
            for child in self.current_page.winfo_children():
                if isinstance(child, ctk.CTkTabview):
                    # Get the currently active tab
                    active_tab_name = child.get()
                    tab_frame = child.tab(active_tab_name)
                    
                    # Find the page widget in the active tab and call its reset method
                    for widget in tab_frame.winfo_children():
                        # Check for various page types and their reset methods
                        if hasattr(widget, 'reset_form'):
                            widget.reset_form()
                            print(f"✅ Reset: {active_tab_name}")
                            return
                        elif hasattr(widget, 'load'):
                            widget.load()
                            print(f"🔄 Refreshed: {active_tab_name}")
                            return
                    break
            
            # For direct pages (like dashboard)
            if hasattr(self.current_page, 'load'):
                self.current_page.load()
                print(f"🔄 Refreshed Dashboard")
        
        except Exception as e:
            print(f"❌ Error resetting page: {e}")
            # Fallback to refresh_views
            self.refresh_views()
    
    def change_save_folder(self):
        cm = ConfigManager()
        current = cm.get_save_dir() or "Not Set"
        if messagebox.askyesno("Change Folder", f"Current Folder:\n{current}\n\nChange it?"):
            d = filedialog.askdirectory(title="Select New Invoice Folder")
            if d:
                cm.set_save_dir(d)
                messagebox.showinfo("Success", f"Updated Save Folder:\n{d}")
