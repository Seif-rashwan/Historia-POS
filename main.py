
import os
import sys

# Add the parent directory to sys.path to allow imports from app package if running from here
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ui.main_window import InventoryApp
from app.utils import optimize_design_images

if __name__ == "__main__":
    # Optimize design images on startup
    optimize_design_images()
    
    app = InventoryApp()
    app.mainloop()
