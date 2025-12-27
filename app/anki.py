import httpx
import json

class AnkiConnectClient:
    def __init__(self, url="http://localhost:8765"):
        self.url = url

    def _invoke(self, action, **params):
        payload = {
            "action": action,
            "version": 6,
            "params": params
        }
        try:
            with httpx.Client() as client:
                response = client.post(self.url, json=payload).json()
            if len(response) != 2:
                raise Exception("response has an unexpected number of fields")
            if "error" not in response:
                raise Exception("response is missing required error field")
            if "result" not in response:
                raise Exception("response is missing required result field")
            if response["error"] is not None:
                raise Exception(response["error"])
            return response["result"]
        except httpx.ConnectError:
            raise Exception("Could not connect to Anki. Is it running with AnkiConnect installed?")

    def check_connection(self):
        try:
            return self._invoke("version") is not None
        except Exception:
            return False

    def get_decks(self):
        return self._invoke("deckNames")

    def create_deck(self, deck_name):
        return self._invoke("createDeck", deck=deck_name)

    def add_note(self, deck_name, front, back):
        params = {
            "note": {
                "deckName": deck_name,
                "modelName": "Basic",
                "fields": {
                    "Front": front,
                    "Back": back
                },
                "options": {
                    "allowDuplicate": False
                },
                "tags": ["anki_inject"]
            }
        }
        return self._invoke("addNote", **params)
