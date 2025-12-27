import customtkinter as ctk
from tkinter import messagebox
from .ai import GeminiClient
from .anki import AnkiConnectClient
import threading

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Anki AI Injector")
        self.geometry("900x700")
        
        # Set appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.ai_client = None
        self.anki_client = AnkiConnectClient()
        self.generated_cards = []

        self._build_ui()

    def _build_ui(self):
        # Grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Preview area expands

        # Header
        self.header_label = ctk.CTkLabel(self, text="Anki AI Flashcard Generator", font=("Inter", 24, "bold"))
        self.header_label.grid(row=0, column=0, pady=20, padx=20)

        # Input Area
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.input_text = ctk.CTkTextbox(self.input_frame, height=150, font=("Inter", 14))
        self.input_text.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.input_text.insert("0.0", "Paste your text here...")

        self.generate_btn = ctk.CTkButton(self.input_frame, text="Generate Flashcards", command=self._on_generate)
        self.generate_btn.grid(row=1, column=0, pady=10)

        # Preview Area
        self.preview_label = ctk.CTkLabel(self, text="Preview & Edit", font=("Inter", 18, "bold"))
        self.preview_label.grid(row=2, column=0, sticky="w", padx=25)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Flashcards")
        self.scrollable_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=10)
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Footer
        self.footer_frame = ctk.CTkFrame(self)
        self.footer_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=20)
        
        self.insert_btn = ctk.CTkButton(self.footer_frame, text="Insert All to Anki", command=self._on_insert, state="disabled", fg_color="green", hover_color="#006400")
        self.insert_btn.pack(pady=10)

    def _on_generate(self):
        text = self.input_text.get("0.0", "end-1c").strip()
        if not text or text == "Paste your text here...":
            messagebox.showwarning("Warning", "Please enter some text.")
            return

        self.generate_btn.configure(state="disabled", text="Generating...")
        
        # Run AI in a separate thread to keep UI responsive
        threading.Thread(target=self._generate_cards_thread, args=(text,), daemon=True).start()

    def _generate_cards_thread(self, text):
        try:
            if not self.ai_client:
                self.ai_client = GeminiClient()
            
            self.generated_cards = self.ai_client.generate_flashcards(text)
            self.after(0, self._render_previews)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.after(0, lambda: self.generate_btn.configure(state="normal", text="Generate Flashcards"))

    def _render_previews(self):
        # Clear existing previews
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.generated_cards:
            messagebox.showinfo("AI Result", "No flashcards were generated.")
            return

        for i, card in enumerate(self.generated_cards):
            card_frame = ctk.CTkFrame(self.scrollable_frame)
            card_frame.grid(row=i, column=0, padx=10, pady=10, sticky="ew")
            card_frame.grid_columnconfigure(1, weight=1)

            # Front Label & Textbox
            ctk.CTkLabel(card_frame, text="Front:").grid(row=0, column=0, padx=10, pady=5, sticky="ne")
            front_text = ctk.CTkTextbox(card_frame, height=60, font=("Inter", 12))
            front_text.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
            front_text.insert("0.0", card.get("front", ""))

            # Back Label & Textbox
            ctk.CTkLabel(card_frame, text="Back:").grid(row=1, column=0, padx=10, pady=5, sticky="ne")
            back_text = ctk.CTkTextbox(card_frame, height=60, font=("Inter", 12))
            back_text.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
            back_text.insert("0.0", card.get("back", ""))

            # Store references to textboxes to retrieve edited content later
            card["front_widget"] = front_text
            card["back_widget"] = back_text

        self.insert_btn.configure(state="normal")

    def _on_insert(self):
        if not self.anki_client.check_connection():
            messagebox.showerror("Anki Error", "Could not connect to Anki. Please make sure Anki is open and AnkiConnect is installed.")
            return

        # Update cards with edited content
        for card in self.generated_cards:
            card["front"] = card["front_widget"].get("0.0", "end-1c")
            card["back"] = card["back_widget"].get("0.0", "end-1c")

        # Insert cards
        success_count = 0
        errors = []
        for card in self.generated_cards:
            try:
                self.anki_client.add_note("Default", card["front"], card["back"])
                success_count += 1
            except Exception as e:
                errors.append(str(e))

        if errors:
            messagebox.showwarning("Insertion Results", f"Inserted {success_count} cards.\nErrors: {len(errors)}\nLast error: {errors[-1]}")
        else:
            messagebox.showinfo("Success", f"Successfully inserted {success_count} cards into Anki!")
