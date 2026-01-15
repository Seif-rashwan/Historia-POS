import sqlite3
import os
import shutil
import glob
from datetime import datetime
from .config import DB_PATH

class DB:
    def __init__(self):
        self.name = DB_PATH
        # Ensure the data directory exists
        db_dir = os.path.dirname(self.name)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        print(f"🔌 Database Path: {self.name}")
        
        self.initialize_schema()
        self.patch_missing_columns()
    
    def get_connection(self):
        return sqlite3.connect(self.name)

    def execute(self, query, params=()):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"❌ SQL Execute Error: {e}\nQuery: {query}\nParams: {params}")
            raise e

    def fetch_all(self, query, params=()):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"❌ SQL FetchAll Error: {e}\nQuery: {query}")
            return []

    def fetch_one(self, query, params=()):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"❌ SQL FetchOne Error: {e}\nQuery: {query}")
            return None

    def backup_database(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            backup_dir = os.path.join(base_dir, "backups")

            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename = f"backup_{timestamp}.db"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            if os.path.exists(self.name):
                shutil.copy2(self.name, backup_path)
                print(f"✅ Backup created: {backup_path}")
                self.cleanup_old_backups(backup_dir)
        except Exception as e:
            print(f"⚠️ Backup error: {e}")
    
    def cleanup_old_backups(self, backup_dir):
        try:
            backup_files = glob.glob(os.path.join(backup_dir, "backup_*.db"))
            backup_files.sort(key=os.path.getmtime, reverse=True)
            if len(backup_files) > 10:
                for old_backup in backup_files[10:]:
                    try: os.remove(old_backup)
                    except: pass
        except: pass

    def initialize_schema(self):
        """
        Initializes the database schema.
        
        FUTURE-PROOFING:
        To add a new table, simply add its 'CREATE TABLE IF NOT EXISTS' statement below.
        The app will automatically create it on the next run without affecting existing data.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Create Tables if they don't exist
                cursor.execute("""CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, customer_id INTEGER, net_total REAL,
                    store_id INTEGER, safe_id INTEGER, payment_method TEXT, delegate_name TEXT, channel TEXT
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, invoice_id INTEGER, 
                    item_detail_id INTEGER, qty REAL, refund_amount REAL, notes TEXT
                )""")
                for table in ['categories', 'colors', 'sizes', 'units', 'stores']:
                    cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
                cursor.execute("""CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, 
                    category_id INTEGER, unit_id INTEGER, code TEXT
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS item_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, barcode TEXT UNIQUE,
                    color_id INTEGER, size_id INTEGER, buy_price REAL DEFAULT 0, 
                    sell_price REAL DEFAULT 0, stock_qty REAL DEFAULT 0,
                    FOREIGN KEY(item_id) REFERENCES items(id)
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS store_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, store_id INTEGER, 
                    item_detail_id INTEGER, quantity REAL DEFAULT 0
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS invoice_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id INTEGER, 
                    item_detail_id INTEGER, qty REAL, price REAL, total REAL, 
                    returned_qty REAL DEFAULT 0
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, from_safe_id INTEGER, 
                    to_safe_id INTEGER, amount REAL, notes TEXT
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS vouchers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, voucher_type TEXT,
                    safe_id INTEGER, amount REAL, description TEXT,
                    customer_id INTEGER, supplier_id INTEGER,
                    FOREIGN KEY (safe_id) REFERENCES safes(id)
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS safes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'Sales'
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS suppliers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, address TEXT, email TEXT, notes TEXT
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, supplier_id INTEGER, 
                    store_id INTEGER, safe_id INTEGER, payment_method TEXT, net_total REAL,
                    tax_percent REAL DEFAULT 0, discount_percent REAL DEFAULT 0,
                    discount_value REAL DEFAULT 0, shipping_cost REAL DEFAULT 0, notes TEXT,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS purchase_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, purchase_id INTEGER, item_detail_id INTEGER,
                    qty REAL, buy_price REAL, total REAL, returned_qty REAL DEFAULT 0,
                    FOREIGN KEY (purchase_id) REFERENCES purchases(id) ON DELETE CASCADE,
                    FOREIGN KEY (item_detail_id) REFERENCES item_details(id)
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS purchase_returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, purchase_id INTEGER,
                    qty REAL, refund_amount REAL, notes TEXT,
                    FOREIGN KEY (purchase_id) REFERENCES purchases(id)
                )""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS purchase_return_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, purchase_return_id INTEGER,
                    purchase_detail_id INTEGER, qty REAL,
                    FOREIGN KEY (purchase_return_id) REFERENCES purchase_returns(id) ON DELETE CASCADE,
                    FOREIGN KEY (purchase_detail_id) REFERENCES purchase_details(id)
                )""")
                conn.commit()
        except Exception as e:
            print(f"❌ Schema Init Error: {e}")

    def patch_missing_columns(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Patch Invoices
                cursor.execute("PRAGMA table_info(invoices)")
                cols = [info[1] for info in cursor.fetchall()]
                new_cols = {
                    "tax_percent": "REAL DEFAULT 0", "discount_percent": "REAL DEFAULT 0",
                    "shipping_cost": "REAL DEFAULT 0", "notes": "TEXT",
                    "paid_amount": "REAL DEFAULT 0", "remaining_amount": "REAL DEFAULT 0"
                }
                for col, dtype in new_cols.items():
                    if col not in cols:
                        print(f"🔧 Patching 'invoices': Adding {col}...")
                        cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col} {dtype}")

                # 2. Patch Purchases (Fixed in previous step)
                cursor.execute("PRAGMA table_info(purchases)")
                p_cols = [info[1] for info in cursor.fetchall()]
                p_new_cols = {
                    "tax_percent": "REAL DEFAULT 0",
                    "discount_percent": "REAL DEFAULT 0",
                    "discount_value": "REAL DEFAULT 0",
                    "shipping_cost": "REAL DEFAULT 0",
                    "notes": "TEXT",
                    "paid_amount": "REAL DEFAULT 0",
                    "remaining_amount": "REAL DEFAULT 0"
                }
                for col, dtype in p_new_cols.items():
                    if col not in p_cols:
                        print(f"🔧 Patching 'purchases': Adding {col}...")
                        cursor.execute(f"ALTER TABLE purchases ADD COLUMN {col} {dtype}")

                # 3. Patch Purchase Details (THE NEW FIX)
                cursor.execute("PRAGMA table_info(purchase_details)")
                pd_cols = [info[1] for info in cursor.fetchall()]
                pd_new_cols = {
                    "buy_price": "REAL DEFAULT 0",
                    "returned_qty": "REAL DEFAULT 0",
                    "total": "REAL DEFAULT 0"
                }
                for col, dtype in pd_new_cols.items():
                    if col not in pd_cols:
                        print(f"🔧 Patching 'purchase_details': Adding {col}...")
                        cursor.execute(f"ALTER TABLE purchase_details ADD COLUMN {col} {dtype}")

                # 4. Patch Returns (For 'no such column: r.invoice_id' error)
                cursor.execute("PRAGMA table_info(returns)")
                r_cols = [info[1] for info in cursor.fetchall()]
                if "invoice_id" not in r_cols:
                    print(f"🔧 Patching 'returns': Adding invoice_id...")
                    cursor.execute("ALTER TABLE returns ADD COLUMN invoice_id INTEGER")

                # 5. Patch Purchase Returns
                cursor.execute("PRAGMA table_info(purchase_returns)")
                pr_cols = [info[1] for info in cursor.fetchall()]
                if "purchase_detail_id" not in pr_cols:
                    cursor.execute("ALTER TABLE purchase_returns ADD COLUMN purchase_detail_id INTEGER")

                # 6. Patch invoice_details (Add cost_at_sale for accurate profit calculation)
                cursor.execute("PRAGMA table_info(invoice_details)")
                id_cols = [info[1] for info in cursor.fetchall()]
                id_new_cols = {
                    "cost_at_sale": "REAL DEFAULT 0",
                    "item_note": "TEXT"
                }
                for col, dtype in id_new_cols.items():
                    if col not in id_cols:
                        print(f"🔧 Patching 'invoice_details': Adding {col}...")
                        cursor.execute(f"ALTER TABLE invoice_details ADD COLUMN {col} {dtype}")

                # 7. Patch purchases (Add parent_purchase_id for manufacturing linkage)
                cursor.execute("PRAGMA table_info(purchases)")
                pur_cols = [info[1] for info in cursor.fetchall()]
                if "parent_purchase_id" not in pur_cols:
                    print(f"🔧 Patching 'purchases': Adding parent_purchase_id...")
                    cursor.execute("ALTER TABLE purchases ADD COLUMN parent_purchase_id INTEGER")

                conn.commit()
                # print("✅ Database Schema Patched Successfully.")
        except Exception as e:
            print(f"⚠️ Patch Error: {e}")