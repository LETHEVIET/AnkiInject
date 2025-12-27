import os
import sys
import time
import threading

def get_asset_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def start_profiler():
    try:
        import psutil
        process = psutil.Process(os.getpid())
        print(f"🚀 Profiler started (PID: {os.getpid()})")
        
        def run_profiler():
            while True:
                mem_mb = process.memory_info().rss / 1024 / 1024
                print(f"📊 Memory Usage: {mem_mb:.2f} MB")
                time.sleep(5)
        
        thread = threading.Thread(target=run_profiler, daemon=True)
        thread.start()
    except ImportError:
        print("❌ psutil not found, profiling disabled.")

def main():
    # Lazy imports to minimize initial RAM footprint
    import webview
    from app.bridge import Bridge
    
    # Optional profiler
    if "--profile" in sys.argv:
        start_profiler()

    # Minimal WebView settings (update instead of overwrite to avoid KeyError)
    webview.settings.update({
        'ALLOW_DOWNLOADS': False,
        'ALLOW_FILE_URLS': True,
        'OPEN_EXTERNAL_LINKS_IN_BROWSER': True,
        'OPEN_DEVTOOLS_IN_DEBUG': False
    })

    # Disable hardware acceleration on Linux to reduce GPU process RAM spikes
    if sys.platform == "linux":
        os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"

    bridge = Bridge()
    
    is_dev = "--dev" in sys.argv
    url = "http://localhost:5173" if is_dev else get_asset_path("frontend/dist/index.html")
    icon_path = "frontend/public/logo.png" if is_dev else get_asset_path("frontend/dist/logo.png")
    
    window = webview.create_window(
        'Anki AI Flashcard Injector',
        url,
        js_api=bridge,
        width=1000,
        height=800,
        background_color='#0f172a',
    )
    
    bridge.set_window(window)
    # Explicitly choosing 'gtk' on Linux for stability and size
    webview.start(gui='gtk', debug=True if is_dev else False)

if __name__ == "__main__":
    main()
