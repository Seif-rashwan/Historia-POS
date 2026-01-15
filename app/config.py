
import os
import customtkinter as ctk

import sys

# Base Directory
if getattr(sys, 'frozen', False):
    # Running as compiled EXE
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running from source
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

DB_PATH = os.path.join(DATA_DIR, "inventory.db")
ICON_PATH = os.path.join(ASSETS_DIR, "app_icon.ico")
OPENING_STOCK_PATH = os.path.join(DATA_DIR, "opening_stock.xlsx")

# Theme & Colors
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Column Widths (from main.py)
COLS = {
    "barcode": 140, "name": 220, "color": 80, "size": 80, 
    "design": 120, "qty": 70, "price": 90, "total": 90, "action": 50
}
