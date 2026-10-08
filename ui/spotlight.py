import customtkinter as ctk
import keyboard
import threading

class SpotlightUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Shadow Automator Spotlight")
        self.geometry("600x60")
        
        # Center window on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (600 / 2)
        y = (screen_height / 4) # Position a bit higher like Mac Spotlight
        self.geometry(f"600x60+{int(x)}+{int(y)}")
        
        # Make window frameless and semi-transparent to mimic blur/transparency effects
        self.overrideredirect(True)
        self.attributes("-alpha", 0.92)
        self.attributes("-topmost", True)
        
        # Theme setup for modern look
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Search Bar UI Elements
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self, 
            textvariable=self.search_var,
            width=580,
            height=40,
            font=("Segoe UI", 20),
            placeholder_text="Enter workflow prompt or target description...",
            corner_radius=10,
            border_width=2,
            border_color="#3b82f6",
            fg_color="#1e293b",
            text_color="white"
        )
        self.search_entry.pack(pady=10, padx=10)
        
        # Bind Escape to hide the search bar
        self.bind("<Escape>", lambda e: self.hide_spotlight())
        # Bind Return to execute the command
        self.search_entry.bind("<Return>", self.on_execute)
        
        self.is_visible = True

    def on_execute(self, event):
        query = self.search_var.get()
        print(f"[Spotlight] Executing: {query}")
        # TODO: Route this event to Member 4's Orchestrator (Phase 3)
        
        self.search_var.set("")
        self.hide_spotlight()

    def toggle_spotlight(self):
        if self.is_visible:
            self.hide_spotlight()
        else:
            self.show_spotlight()

    def hide_spotlight(self):
        self.withdraw()
        self.is_visible = False

    def show_spotlight(self):
        self.deiconify()
        self.focus_force()
        self.search_entry.focus()
        self.is_visible = True

def hotkey_listener(app):
    """
    Listens for the Ctrl + Space hotkey globally to toggle the Spotlight UI.
    """
    keyboard.add_hotkey('ctrl+space', app.toggle_spotlight)
    keyboard.wait() # Block the thread

if __name__ == "__main__":
    app = SpotlightUI()
    
    # Run the global hotkey listener in a background thread so it doesn't block the UI
    listener_thread = threading.Thread(target=hotkey_listener, args=(app,), daemon=True)
    listener_thread.start()
    
    app.mainloop()
