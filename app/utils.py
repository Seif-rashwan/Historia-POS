
import os
import sys
import pandas as pd
import webbrowser
from datetime import datetime

# --- Arabic Text Fixer ---
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_AVAILABLE = True
except ImportError:
    ARABIC_AVAILABLE = False
    print("Warning: arabic_reshaper or python-bidi not installed. Arabic text may not display correctly.")

def fix_text(text):
    if not text: return ""
    if not ARABIC_AVAILABLE: return text
    try:
        reshaped_text = arabic_reshaper.reshape(str(text))
        return get_display(reshaped_text)
    except:
        return text

# --- PDF Export Libraries ---
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, A5
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not installed. PDF export will not work.")

# --- Barcode Library ---
try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False
    print("Warning: python-barcode not installed. Barcode generation will not work.")

# --- Matplotlib for Charts ---
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib
    matplotlib.use('TkAgg')
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not installed. Charts will not work.")

# --- WhatsApp Integration ---
WHATSAPP_AVAILABLE = True  # Using webbrowser which is standard lib
# --- Pillow for Image Optimization ---
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("Warning: Pillow not installed. Image optimization will not work.")

def optimize_design_images():
    """
    Optimizes raw design images for gallery display.
    Converts PNG/JPG to small JPG thumbnails (150x150) with white background.
    """
    if not PILLOW_AVAILABLE: return

    RAW_DIR = os.path.join("assets", "designs", "raw")
    PROCESSED_DIR = os.path.join("assets", "designs", "processed")

    if not os.path.exists(RAW_DIR):
        try: os.makedirs(RAW_DIR)
        except: pass
        return # Nothing to process if dir didn't exist
    
    if not os.path.exists(PROCESSED_DIR):
        try: os.makedirs(PROCESSED_DIR)
        except: pass

    count = 0
    for filename in os.listdir(RAW_DIR):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            name, ext = os.path.splitext(filename)
            target_file = f"{name}.jpg"
            target_path = os.path.join(PROCESSED_DIR, target_file)
            
            # Skip if already exists (Simple Caching)
            if os.path.exists(target_path): continue
            
            try:
                source_path = os.path.join(RAW_DIR, filename)
                img = Image.open(source_path)
                
                # Create White Background for Transparency
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                    img = bg
                else:
                    img = img.convert("RGB")
                    
                # Resize (Thumbnail)
                img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                
                # Save
                img.save(target_path, "JPEG", quality=85, optimize=True)
                count += 1
                print(f"Optimized: {filename} -> {target_file}")
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
                
    if count > 0: print(f"Optimization Complete: {count} new images processed.")
