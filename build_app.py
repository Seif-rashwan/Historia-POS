
import PyInstaller.__main__
import os

def build():
    # Define assets path
    assets_path = os.path.join("assets")
    icon_path = os.path.join(assets_path, "app_icon.ico")
    
    print("🚀 Starting Build Process for HistoriaPOS...")
    
    PyInstaller.__main__.run([
        'main.py',                       # Main script
        '--name=HistoriaPOS',            # Name of the executable
        '--onedir',                      # One Directory build
        '--noconsole',                   # Hide console
        f'--icon={icon_path}',           # Icon
        f'--add-data={assets_path}{os.pathsep}assets', # Include assets folder
        '--clean',                       # Clean cache
        '--noconfirm',                   # Overwrite existing
        # '--windowed',                  # Same as noconsole (explicit check)
    ])
    
    print("\n✅ Build Completed!")
    print(f"📂 Output Folder: {os.path.join(os.getcwd(), 'dist', 'HistoriaPOS')}")

if __name__ == "__main__":
    build()
