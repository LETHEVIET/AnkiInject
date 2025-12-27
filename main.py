import webview
import os
import sys
from app.bridge import Bridge

def get_asset_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def main():
    bridge = Bridge()
    
    # In development, we might want to point to the Vite dev server
    # For now, we'll assume the frontend will be built or we can provide a dev flag
    is_dev = "--dev" in sys.argv
    url = "http://localhost:5173" if is_dev else get_asset_path("frontend/dist/index.html")
    
    # Icon path: In dev use local, in prod use bundled in dist
    icon_path = "frontend/public/logo.png" if is_dev else get_asset_path("frontend/dist/logo.png")
    
    window = webview.create_window(
        'Anki AI Flashcard Injector',
        url,
        js_api=bridge,
        width=1000,
        height=800,
        background_color='#0f172a',
        # resizable=True, # Default is True
        # min_size=(800, 600),
    )
    
    bridge.set_window(window)
    # On Linux, explicitly choosing 'gtk' can help if double-loading occurs
    # 'debug=True' is handled by argv check
    webview.start(gui='gtk', debug=True if "--dev" in sys.argv else False)

if __name__ == "__main__":
    main()
