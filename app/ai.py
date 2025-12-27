from google import genai
from google.genai import types
from pydantic import BaseModel
import os
import json
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Flashcard(BaseModel):
    front: str
    back: str

class FlashcardList(BaseModel):
    cards: list[Flashcard]

class GeminiClient:
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

    def set_api_key(self, api_key):
        self.api_key = api_key
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def _ensure_client(self):
        if not self.client:
            raise ValueError("Gemini API Key is not configured. Please go to Settings to add your key.")

    def refine_flashcard(self, front, back, instruction, model='gemini-1.5-flash'):
        self._ensure_client()
        prompt = f"""
        Refine the following flashcard based on this instruction: "{instruction}"
        
        Current Front: {front}
        Current Back: {back}
        
        Ensure the output is a single, improved flashcard. 
        Focus strictly on the provided instruction while maintaining clarity and accuracy.
        Use basic HTML tags (<b>, <i>, <ul>, <li>) for rich text formatting.
        """
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=Flashcard,
            ),
        )
        return response.parsed

    DEFAULT_SYSTEM_PROMPT = """
        Extract key information from the following text and create flashcards.
        The 'front' should be a question or concept, and 'back' should be the answer or explanation.
        Use basic HTML tags where appropriate for formatting (e.g., <b>bold</b>, <i>italics</i>, <ul><li>lists</li></ul>).
    """

    def generate_flashcards(self, text, model='gemini-1.5-flash', system_instruction=None):
        self._ensure_client()
        
        instruction = system_instruction if system_instruction else self.DEFAULT_SYSTEM_PROMPT
        
        prompt = f"""
        {instruction}
        
        Text:
        {text}
        """
        
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': FlashcardList,
            }
        )
        
        data = json.loads(response.text)
        return data.get("cards", [])
