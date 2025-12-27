import webview
from .ai import GeminiClient
from .anki import AnkiConnectClient
import os
import json
import gc
from pathlib import Path
import pyperclip

class Bridge:
    def __init__(self):
        self._window = None
        self.ai_client = GeminiClient()
        self.anki_client = AnkiConnectClient()

    def read_clipboard(self):
        try:
            text = pyperclip.paste()
            return {"status": "success", "text": text}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def set_window(self, window):
        self._window = window

    def _get_config_path(self):
        """Standard cross-platform config path: ~/.config/anki-inject/config.json"""
        if os.name == 'nt': # Windows
            base_dir = Path(os.environ.get('APPDATA', '~')).expanduser()
        else: # Linux/Mac
            base_dir = Path('~/.config').expanduser()
        
        config_dir = base_dir / "anki-inject"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"

    def get_settings(self):
        config_path = self._get_config_path()
        default_prompt = self.ai_client.DEFAULT_SYSTEM_PROMPT
        
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    return {
                        "gemini_api_key": config.get("gemini_api_key", self.ai_client.api_key or ""),
                        "ai_system_prompt": config.get("ai_system_prompt") or default_prompt
                    }
            except:
                pass
        
        return {
            "gemini_api_key": self.ai_client.api_key or "",
            "ai_system_prompt": default_prompt
        }

    def save_settings(self, api_key, ai_system_prompt=""):
        try:
            # Update the client
            self.ai_client.set_api_key(api_key)
            
            # Persist to JSON config
            config_path = self._get_config_path()
            config = {
                "gemini_api_key": api_key,
                "ai_system_prompt": ai_system_prompt
            }
            
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
                
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_decks(self):
        try:
            decks = self.anki_client.get_decks()
            return {"status": "success", "decks": decks}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def create_deck(self, deck_name):
        try:
            self.anki_client.create_deck(deck_name)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def refine_card(self, front, back, instruction, model_name='gemini-1.5-flash'):
        try:
            refined = self.ai_client.refine_flashcard(front, back, instruction, model=model_name)
            return {"status": "success", "card": {"front": refined.front, "back": refined.back}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def generate_cards(self, text, model_name='gemini-1.5-flash', custom_prompt=None):
        try:
            cards = self.ai_client.generate_flashcards(text, model=model_name, system_instruction=custom_prompt)
            return {"status": "success", "cards": cards}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def generate_cards_stream(self, text, model_name='gemini-1.5-flash', custom_prompt=None):
        if not self._window:
             return {"status": "error", "message": "Window handle not available"}
             
        try:
            for card in self.ai_client.generate_flashcards_stream(text, model=model_name, system_instruction=custom_prompt):
                # Send card to frontend immediately
                js_code = f"window.receiveCard({json.dumps(card)})"
                self._window.evaluate_js(js_code)
            
            # Help GC after stream
            gc.collect()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}




    def insert_cards(self, cards, deck_name="Default"):
        if not self.anki_client.check_connection():
            return {"status": "error", "message": "Could not connect to Anki. Ensure it's running with AnkiConnect."}

        success_count = 0
        duplicate_count = 0
        errors = []
        for card in cards:
            try:
                self.anki_client.add_note(deck_name, card["front"], card["back"])
                success_count += 1
            except Exception as e:
                err_msg = str(e).lower()
                if "duplicate" in err_msg:
                    duplicate_count += 1
                else:
                    errors.append(str(e))

        return {
            "status": "success", 
            "count": success_count, 
            "duplicates": duplicate_count, 
            "errors": errors
        }
    
    def clear_cache(self):
        """Manually trigger garbage collection"""
        gc.collect()
        return {"status": "success"}
