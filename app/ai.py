from google import genai
from google.genai import types
from pydantic import BaseModel
import os
import json
import re
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Flashcard(BaseModel):
    front: str
    back: str

class FlashcardList(BaseModel):
    cards: list[Flashcard]

class GeminiClient:
    DEFAULT_SYSTEM_PROMPT = """
    You are an expert flashcard creator for Anki.
    Your goal is to extract knowledge from the provided text and convert it into high-quality flashcards.
    
    Rules:
    1. Create atomic cards (one concept per card).
    2. Use simple, direct questions for the FRONT.
    3. Use concise, clear answers for the BACK.
    4. Use bolding (<b>) for key terms.
    5. Use lists (<ul><li>...</li></ul>) if there are multiple steps or points.
    6. Do not include standard introductory text.
    7. Return a JSON object with a "cards" key containing a list of objects.
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        
        # 1. Try to load from native global config
        if not self.api_key:
            try:
                if os.name == 'nt':
                    base_dir = Path(os.environ.get('APPDATA', '~')).expanduser()
                else:
                    base_dir = Path('~/.config').expanduser()
                config_path = base_dir / "anki-inject" / "config.json"
                if config_path.exists():
                    with open(config_path, "r") as f:
                        config = json.load(f)
                        self.api_key = config.get("gemini_api_key")
            except:
                pass

        # 2. Fallback to .env / os.getenv
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")

        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def set_api_key(self, key):
        self.api_key = key
        # Reset client with new key
        self.client = genai.Client(api_key=self.api_key)

    def _ensure_key(self):
        if not self.client:
             if self.api_key:
                 self.client = genai.Client(api_key=self.api_key)
             else:
                 raise ValueError("API Key not found. Please set it in settings.")

    def _get_model_name(self, model_id):
        # google-genai uses just 'gemini-1.5-flash', etc.
        # But we need to handle if we were passing 'gemini/' prefix from frontend or litellm habit
        if model_id.startswith("gemini/"):
            return model_id.replace("gemini/", "")
        return model_id

    def refine_flashcard(self, front, back, instruction, model='gemini-1.5-flash'):
        self._ensure_key()
        prompt = f"""
        Refine the following flashcard based on this instruction: "{instruction}"
        
        Current Front: {front}
        Current Back: {back}
        
        Ensure the output is a single, improved flashcard in JSON format. 
        Focus strictly on the provided instruction while maintaining clarity and accuracy.
        Use basic HTML tags (<b>, <i>, <ul>, <li>) for rich text formatting.
        """
        
        response = self.client.models.generate_content(
            model=self._get_model_name(model),
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_schema=Flashcard,
                response_mime_type="application/json"
            )
        )
        
        try:
            # v0.3+ parsed property
            return response.parsed
        except:
            # Fallback
            return Flashcard(**json.loads(response.text))

    def generate_flashcards(self, text, model='gemini-1.5-flash', system_instruction=None):
        cards = []
        for card in self.generate_flashcards_stream(text, model, system_instruction):
            cards.append(card)
        return cards

    def generate_flashcards_stream(self, text, model='gemini-1.5-flash', system_instruction=None):
        self._ensure_key()
        
        instruction = system_instruction if system_instruction else self.DEFAULT_SYSTEM_PROMPT
        
        response = self.client.models.generate_content_stream(
            model=self._get_model_name(model),
            contents=[text],
            config=types.GenerateContentConfig(
                system_instruction=instruction,
                response_mime_type="application/json",
                response_schema=FlashcardList
            )
        )

        buffer = ""
        in_array = False
        
        for chunk in response:
            # google-genai yields chunks with .text
            delta = chunk.text
            if not delta:
                continue
            
            buffer += delta
            
            if not in_array:
                # Look for the start of the cards array: "cards": [ or just [
                match = re.search(r'"cards"\s*:\s*\[', buffer)
                if match:
                    buffer = buffer[match.end():]
                    in_array = True
                else:
                    # Fallback for if it's just a raw array [ ... ]
                    idx = buffer.find('[')
                    if idx != -1:
                        # Ensure it's not part of an object key or something
                        # This is a bit of a gamble, but if we haven't found "cards": [ yet,
                        # and we encounter a [, it might be the start.
                        # Simple heuristic: if it's the very first char after optional { and whitespace
                        temp_buf = buffer.lstrip().lstrip('{').lstrip()
                        if temp_buf.startswith('['):
                            buffer = buffer[idx + 1:]
                            in_array = True

            if in_array:
                depth = 0
                current_obj_start = -1
                in_string = False
                escape_next = False
                
                i = 0
                while i < len(buffer):
                    char = buffer[i]
                    
                    if in_string:
                        if escape_next:
                            escape_next = False
                        elif char == '\\':
                            escape_next = True
                        elif char == '"':
                            in_string = False
                    else:
                        if char == '"':
                            in_string = True
                        elif char == '{':
                            if depth == 0:
                                current_obj_start = i
                            depth += 1
                        elif char == '}':
                            depth -= 1
                            if depth == 0 and current_obj_start != -1:
                                # Found valid object
                                json_str = buffer[current_obj_start : i+1]
                                try:
                                    card_dict = json.loads(json_str)
                                    yield card_dict
                                except json.JSONDecodeError as e:
                                    pass
                                
                                buffer = buffer[i+1:]
                                i = -1
                                current_obj_start = -1
                                depth = 0
                                in_string = False
                                escape_next = False
                    
                    i += 1







