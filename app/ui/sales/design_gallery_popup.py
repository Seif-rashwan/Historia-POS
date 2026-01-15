import customtkinter as ctk
import os
from PIL import Image

class DesignGalleryPopup(ctk.CTkToplevel):
    def __init__(self, parent, db, callback):
        super().__init__(parent)
        self.db = db
        self.callback = callback
        self.title("Select Design")
        self.geometry("800x600")
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # --- Search ---
        top_frame = ctk.CTkFrame(self, height=50)
        top_frame.pack(fill="x", padx=10, pady=10)
        
        self.ent_search = ctk.CTkEntry(top_frame, placeholder_text="Search Design...", width=300, font=("Arial", 14))
        self.ent_search.pack(side="left", padx=10)
        self.ent_search.bind("<KeyRelease>", self.filter_designs)
        
        # --- Grid ---
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Load Data
        self.designs = [] # List of dicts {barcode, name, path}
        self.load_design_data()
        self.render_grid()
        
    def load_design_data(self):
        # Fetch HD items
        items = self.db.fetch_all("SELECT barcode, name FROM item_details d JOIN items i ON d.item_id=i.id WHERE d.barcode LIKE 'HD%'")
        
        processed_dir = os.path.join("assets", "designs", "processed")
        
        self.designs = []
        for bar, name in items:
            # Check for image
            img_path = None
            candidate = os.path.join(processed_dir, f"{bar}.jpg")
            if os.path.exists(candidate):
                img_path = candidate
            
            self.designs.append({
                "barcode": bar,
                "name": name,
                "image_path": img_path
            })
            
    def render_grid(self, query=""):
        # Clear existing
        for w in self.scroll_frame.winfo_children(): w.destroy()
        
        query = query.lower().strip()
        filtered = [d for d in self.designs if query in d["name"].lower() or query in d["barcode"].lower()]
        
        if not filtered:
            ctk.CTkLabel(self.scroll_frame, text="No designs found", font=("Arial", 16)).pack(pady=20)
            return

        # Grid config
        cols = 5
        for i, d in enumerate(filtered):
            r = i // cols
            c = i % cols
            
            card = ctk.CTkFrame(self.scroll_frame, width=140, height=180)
            card.grid(row=r, column=c, padx=10, pady=10)
            
            # Load Image
            img_obj = None
            if d["image_path"]:
                try:
                    pil_img = Image.open(d["image_path"])
                    img_obj = ctk.CTkImage(pil_img, size=(100, 100))
                except: pass
            
            # If no image, maybe a placeholder or text
            if not img_obj:
               # Simple placeholder text logic? Or just text button
               btn = ctk.CTkButton(card, text=f"{d['barcode']}\nNo Img", width=120, height=120, fg_color="gray", command=lambda b=d['barcode']: self.on_select(b))
            else:
               btn = ctk.CTkButton(card, text="", image=img_obj, width=120, height=120, fg_color="transparent", hover_color="gray80", command=lambda b=d['barcode']: self.on_select(b))
               
            btn.pack(pady=5)
            
            lbl = ctk.CTkLabel(card, text=d["name"][:15], font=("Arial", 10))
            lbl.pack(pady=2)
            lbl2 = ctk.CTkLabel(card, text=d["barcode"], font=("Arial", 10, "bold"), text_color="gray50")
            lbl2.pack(pady=0)

    def filter_designs(self, e=None):
        self.render_grid(self.ent_search.get())

    def on_select(self, barcode):
        if self.callback:
            self.callback(barcode)
        self.destroy()
