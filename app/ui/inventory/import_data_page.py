
import customtkinter as ctk
from tkinter import filedialog, messagebox
import pandas as pd
from datetime import date
from app.database import DB
from app.utils import fix_text

class ImportDataPage(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.db = DB()
        self.controller = controller
        
        # Fonts
        self.AR_FONT = ("Segoe UI", 12)
        self.AR_FONT_BOLD = ("Segoe UI", 13, "bold")
        self.AR_FONT_HEADER = ("Segoe UI", 20, "bold")
        
        # 1. Header
        header = ctk.CTkFrame(self, height=60, fg_color="gray20")
        header.pack(side="top", fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text=fix_text("استيراد البيانات (Excel)"), 
                     font=self.AR_FONT_HEADER, text_color="#3498DB").pack(side="right", padx=20)

        # 2. Main Content Split
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        
        # === RIGHT PANEL (Controls) ===
        right_panel = ctk.CTkFrame(content, width=300)
        right_panel.pack(side="right", fill="y", padx=5)
        
        ctk.CTkLabel(right_panel, text=fix_text("1. اختر نوع الاستيراد"), font=self.AR_FONT_BOLD).pack(pady=(20, 10))
        
        # --- Selector (The New Feature) ---
        self.import_type = ctk.StringVar(value="Orders")
        # Values in English for logic, displayed in Arabic
        self.type_selector = ctk.CTkSegmentedButton(
            right_panel, 
            values=["Orders", "Vouchers", "Transfers"],
            variable=self.import_type,
            font=self.AR_FONT_BOLD,
            selected_color="#E67E22",
            height=40
        )
        self.type_selector.pack(pady=5, padx=20, fill="x")
        # Change labels to Arabic visually
        self.type_selector.configure(values=[fix_text("فواتير بيع"), fix_text("سندات مالية"), fix_text("تحويل مخزني")])
        self.type_selector.set(fix_text("فواتير بيع")) # Default
        
        ctk.CTkLabel(right_panel, text="_______________________", text_color="gray").pack(pady=10)

        ctk.CTkButton(right_panel, text="📥 Download Template", 
                      command=self.download_template, fg_color="#2980B9", 
                      font=("Arial", 13, "bold"), height=40).pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(right_panel, text=fix_text("املأ القالب ثم ارفعه هنا:"), font=self.AR_FONT, text_color="gray").pack(pady=(5,5))
        
        ctk.CTkButton(right_panel, text="📤 Upload Excel File", 
                      command=self.upload_file, fg_color="#27AE60", 
                      font=("Arial", 13, "bold"), height=40).pack(pady=5, padx=20, fill="x")
        
        self.progress = ctk.CTkProgressBar(right_panel)
        self.progress.pack(pady=20, padx=20, fill="x")
        self.progress.set(0)
        
        self.lbl_status = ctk.CTkLabel(right_panel, text="Ready...", font=("Arial", 12))
        self.lbl_status.pack(pady=5)

        # === LEFT PANEL (Log & Errors) ===
        left_panel = ctk.CTkFrame(content)
        left_panel.pack(side="left", fill="both", expand=True, padx=5)
        
        ctk.CTkLabel(left_panel, text="Process Log", font=("Arial", 14, "bold")).pack(pady=(10, 5))
        
        # Footer (Error Button)
        footer_frame = ctk.CTkFrame(left_panel, fg_color="gray25", height=100)
        footer_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        self.lbl_summary = ctk.CTkLabel(footer_frame, text="", font=("Arial", 12, "bold"), text_color="#F39C12")
        self.lbl_summary.pack(side="top", pady=5)
        
        self.btn_errors = ctk.CTkButton(footer_frame, text="📥 Download Errors Report", 
                                      command=self.download_errors, fg_color="gray", 
                                      font=("Arial", 13, "bold"), height=45, state="disabled")
        self.btn_errors.pack(side="bottom", fill="x", padx=20, pady=10)
        
        # Log Box
        self.txt_log = ctk.CTkTextbox(left_panel, font=("Consolas", 11))
        self.txt_log.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        
        self.errors_df = None

    def log(self, message):
        self.txt_log.insert("end", str(message) + "\n")
        self.txt_log.see("end")
        self.update() 
        
    def get_current_mode(self):
        val = self.type_selector.get()
        if val == fix_text("فواتير بيع"): return "Orders"
        if val == fix_text("سندات مالية"): return "Vouchers"
        if val == fix_text("تحويل مخزني"): return "Transfers"
        return "Orders"

    def download_template(self):
        mode = self.get_current_mode()
        try:
            data = {}
            fname = "template.xlsx"
            
            if mode == "Orders":
                fname = "orders_template.xlsx"
                data = {
                    "Reference": ["1", "1", "2"], "Date": [str(date.today())]*3, "Customer": ["Ahmed", "Ahmed", "Sarah"],
                    "Store": ["Main Store"]*3, "Barcode": ["ITEM001", "ITEM002", "ITEM003"],
                    "Qty": [1, 2, 5], "Price": [100, 50, 200], "Channel": ["Store", "Instagram", "Website"], 
                    "Payment_Method": ["Cash", "Visa", "Instapay"], "Delegate": ["Ahmed", "Arrive", ""]
                }
            elif mode == "Vouchers":
                fname = "vouchers_template.xlsx"
                data = {
                    "Date": [str(date.today()), str(date.today())],
                    "Type": ["Receipt", "Payment"], # قبض / صرف
                    "Safe": ["Main Treasury (Cash)", "Bank Account (Visa)"],
                    "Amount": [5000, 150],
                    "Description": ["Opening Balance", "Electricity Bill"]
                }
            elif mode == "Transfers":
                fname = "stock_transfer_template.xlsx"
                data = {
                    "Date": [str(date.today())],
                    "From_Store": ["Main Store"],
                    "To_Store": ["Secondary Store"],
                    "Barcode": ["ITEM001"],
                    "Qty": [10]
                }

            path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], initialfile=fname)
            if path:
                pd.DataFrame(data).to_excel(path, index=False)
                messagebox.showinfo("Success", f"{mode} Template downloaded successfully.")
        except Exception as e: messagebox.showerror("Error", str(e))

    def upload_file(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if not path: return
        
        self.progress.set(0.1)
        self.lbl_status.configure(text="Reading file...")
        self.btn_errors.configure(state="disabled", fg_color="gray", text="Processing...")
        self.update() 
        
        mode = self.get_current_mode()
        
        try:
            df = pd.read_excel(path)
            # Clean columns
            df.columns = [str(c).strip() for c in df.columns]
            
            if mode == "Orders":
                self.process_orders(df)
            elif mode == "Vouchers":
                self.process_vouchers(df)
            elif mode == "Transfers":
                self.process_transfers(df)
                
        except Exception as e:
            self.log(f"Critical Error: {e}")
            messagebox.showerror("Error", f"File Error:\n{e}")
            self.progress.set(0)

    def process_orders(self, df):
        self.txt_log.delete("1.0", "end")
        self.log("Mode: Sales Orders Import")
        self.log(f"File loaded: {len(df)} rows.")
        
        grouped = df.groupby("Reference")
        errors = []
        success_inv = 0
        total_items = 0
        
        for ref, group in grouped:
            ref_str = str(ref)
            
            # Duplicate Check
            if self.db.fetch_one("SELECT id FROM invoices WHERE notes LIKE ?", (f"%Ref: {ref_str}%",)):
                self.log(f">> Ref {ref}: Skipped (Duplicate)")
                continue

            valid_invoice = True; invoice_error = ""; valid_items = []
            first = group.iloc[0]
            store = str(first.get("Store", "")).strip()
            
            store_res = self.db.fetch_one("SELECT id FROM stores WHERE name=?", (store,))
            if not store_res:
                valid_invoice = False; invoice_error = f"Store '{store}' not found"
            else:
                store_id = store_res[0]
                for _, row in group.iterrows():
                    bc = str(row.get("Barcode", "")).strip().upper()
                    item_res = self.db.fetch_one("SELECT id FROM item_details WHERE barcode=?", (bc,))
                    if not item_res:
                        valid_invoice = False; invoice_error = f"Barcode '{bc}' not found"
                        break
                    try: q = float(row.get("Qty", 0)); p = float(row.get("Price", 0))
                    except: valid_invoice = False; invoice_error = "Invalid Qty/Price"; break
                    valid_items.append({"did": item_res[0], "qty": q, "p": p, "bc": bc})

            if not valid_invoice:
                self.log(f"XX Ref {ref}: Rejected ({invoice_error})")
                for _, row in group.iterrows():
                    err_row = row.to_dict(); err_row["Error_Reason"] = invoice_error
                    errors.append(err_row)
            else:
                cust_name = str(first.get("Customer", "General")).strip()
                cust_id = self.db.fetch_one("SELECT id FROM customers WHERE name=?", (cust_name,))
                if not cust_id: cust_id = self.db.execute("INSERT INTO customers (name) VALUES (?)", (cust_name,))
                else: cust_id = cust_id[0]
                
                d_val = first.get("Date", date.today())
                try: d_str = pd.to_datetime(d_val, dayfirst=True).date()
                except: d_str = date.today()

                channel = str(first.get("Channel", "Store")).strip()
                delegate = str(first.get("Delegate", "")).strip()
                pay_method = str(first.get("Payment_Method", "Cash")).strip()
                total = sum(x["qty"]*x["p"] for x in valid_items)
                
                inv_id = self.db.execute("""INSERT INTO invoices (date, customer_id, net_total, paid_amount, remaining_amount, store_id, safe_id, payment_method, channel, delegate_name, notes) 
                                            VALUES (?,?,?,?,0,?,1,?,?,?,?)""", 
                                       (str(d_str), cust_id, total, total, store_id, pay_method, channel, delegate, f"Ref: {ref_str}"))
                
                for item in valid_items:
                    self.db.execute("INSERT INTO invoice_details (invoice_id, item_detail_id, qty, price, total) VALUES (?,?,?,?,?)", 
                                   (inv_id, item["did"], item["qty"], item["p"], item["qty"]*item["p"]))
                    has_stock = self.db.fetch_one("SELECT 1 FROM store_stock WHERE item_detail_id=? AND store_id=?", (item["did"], store_id))
                    if has_stock: self.db.execute("UPDATE store_stock SET quantity=quantity-? WHERE item_detail_id=? AND store_id=?", (item["qty"], item["did"], store_id))
                    else: self.db.execute("INSERT INTO store_stock (item_detail_id, store_id, quantity) VALUES (?,?,?)", (item["did"], store_id, -item["qty"]))
                
                success_inv += 1; total_items += len(valid_items)
                self.log(f"OK Ref {ref}: Imported ({len(valid_items)} items)")

        self.finish_process(errors, f"Success: {success_inv} Invoices")

    def process_vouchers(self, df):
        self.txt_log.delete("1.0", "end")
        self.log("Mode: Vouchers (Receipts/Payments)")
        errors = []
        count = 0
        
        for idx, row in df.iterrows():
            try:
                # Type Validation
                v_type = str(row.get("Type", "")).strip()
                # Map various inputs to standard Receipt/Payment
                if v_type.lower() in ["receipt", "in", "قبض", "ايراد"]: db_type = "Receipt"
                elif v_type.lower() in ["payment", "out", "صرف", "مصروف"]: db_type = "Payment"
                else: raise ValueError(f"Invalid Type: {v_type}")

                # Safe Validation
                safe_name = str(row.get("Safe", "")).strip()
                safe_res = self.db.fetch_one("SELECT id FROM safes WHERE name=?", (safe_name,))
                if not safe_res: raise ValueError(f"Safe '{safe_name}' not found")
                safe_id = safe_res[0]

                # Date
                d_val = row.get("Date", date.today())
                try: d_str = pd.to_datetime(d_val, dayfirst=True).date()
                except: d_str = date.today()

                # Amount
                amount = float(row.get("Amount", 0))
                desc = str(row.get("Description", "Imported"))

                self.db.execute("INSERT INTO vouchers (date, voucher_type, safe_id, amount, description) VALUES (?,?,?,?,?)",
                               (str(d_str), db_type, safe_id, amount, desc))
                count += 1
                self.log(f"Row {idx+2}: Imported {db_type} - {amount}")

            except Exception as e:
                self.log(f"Row {idx+2}: Failed ({e})")
                err_row = row.to_dict(); err_row["Error_Reason"] = str(e)
                errors.append(err_row)

        self.finish_process(errors, f"Imported: {count} Vouchers")

    def process_transfers(self, df):
        self.txt_log.delete("1.0", "end")
        self.log("Mode: Stock Transfers (Between Stores)")
        errors = []
        count = 0

        for idx, row in df.iterrows():
            try:
                # Validate Stores
                from_s = str(row.get("From_Store", "")).strip()
                to_s = str(row.get("To_Store", "")).strip()
                
                s1 = self.db.fetch_one("SELECT id FROM stores WHERE name=?", (from_s,))
                s2 = self.db.fetch_one("SELECT id FROM stores WHERE name=?", (to_s,))
                
                if not s1: raise ValueError(f"From_Store '{from_s}' not found")
                if not s2: raise ValueError(f"To_Store '{to_s}' not found")
                if s1[0] == s2[0]: raise ValueError("Source and Destination stores are the same")

                # Validate Item
                bc = str(row.get("Barcode", "")).strip().upper()
                item_res = self.db.fetch_one("SELECT id FROM item_details WHERE barcode=?", (bc,))
                if not item_res: raise ValueError(f"Barcode '{bc}' not found")
                did = item_res[0]

                # Qty
                qty = float(row.get("Qty", 0))
                if qty <= 0: raise ValueError("Qty must be positive")

                # Check Stock in Source
                stock_res = self.db.fetch_one("SELECT quantity FROM store_stock WHERE item_detail_id=? AND store_id=?", (did, s1[0]))
                current_stock = stock_res[0] if stock_res else 0
                
                if current_stock < qty:
                    raise ValueError(f"Insufficient stock in '{from_s}'. Has {current_stock}, Requested {qty}")

                # EXECUTE TRANSFER
                # 1. Deduct from Source
                self.db.execute("UPDATE store_stock SET quantity=quantity-? WHERE item_detail_id=? AND store_id=?", (qty, did, s1[0]))
                
                # 2. Add to Destination
                has_dest = self.db.fetch_one("SELECT 1 FROM store_stock WHERE item_detail_id=? AND store_id=?", (did, s2[0]))
                if has_dest:
                    self.db.execute("UPDATE store_stock SET quantity=quantity+? WHERE item_detail_id=? AND store_id=?", (qty, did, s2[0]))
                else:
                    self.db.execute("INSERT INTO store_stock (item_detail_id, store_id, quantity) VALUES (?,?,?)", (did, s2[0], qty))

                count += 1
                self.log(f"Row {idx+2}: Transferred {qty} of {bc}")

            except Exception as e:
                self.log(f"Row {idx+2}: Failed ({e})")
                err_row = row.to_dict(); err_row["Error_Reason"] = str(e)
                errors.append(err_row)

        self.finish_process(errors, f"Transferred: {count} Items")

    def finish_process(self, errors, success_msg):
        self.progress.set(1.0)
        self.lbl_status.configure(text="Finished")
        
        if errors:
            self.errors_df = pd.DataFrame(errors)
            self.btn_errors.configure(state="normal", fg_color="#E74C3C", text=f"📥 Download Errors ({len(errors)} rows)")
            self.lbl_summary.configure(text=f"{success_msg} | Errors: {len(errors)}", text_color="#E74C3C")
            self.log(f"\n⚠️ Completed with errors. Check report.")
            messagebox.showwarning("Attention", "Operation completed with some errors.\nPlease download the error report.")
        else:
            self.btn_errors.configure(state="disabled", fg_color="gray", text="No Errors Found")
            self.lbl_summary.configure(text=success_msg, text_color="#27AE60")
            messagebox.showinfo("Success", "Import Completed Successfully!")

    def download_errors(self):
        if self.errors_df is not None:
            path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], initialfile="import_errors.xlsx")
            if path:
                self.errors_df.to_excel(path, index=False)
                messagebox.showinfo("Saved", "Error report saved successfully.")
