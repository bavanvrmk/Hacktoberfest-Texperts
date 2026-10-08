import customtkinter as ctk
import keyboard
import threading
import time

class ToastNotification(ctk.CTkToplevel):
    def __init__(self, parent, message, color="#10b981"):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-alpha", 0.0)
        self.attributes("-topmost", True)
        
        # Geometry and positioning (Center Top)
        screen_width = self.winfo_screenwidth()
        self.geometry(f"450x60+{int(screen_width/2 - 225)}+40")
        
        # Card background
        self.frame = ctk.CTkFrame(self, fg_color="#1e293b", border_width=2, border_color=color, corner_radius=15)
        self.frame.pack(fill="both", expand=True)
        
        # Text
        self.label = ctk.CTkLabel(self.frame, text=message, font=("Segoe UI", 16, "bold"), text_color="white")
        self.label.pack(pady=15)
        
        self.animate_in()
        
    def animate_in(self, alpha=0.0):
        if alpha < 0.95:
            alpha += 0.1
            self.attributes("-alpha", alpha)
            self.after(20, self.animate_in, alpha)
        else:
            self.after(3000, self.animate_out)
            
    def animate_out(self, alpha=0.95):
        if alpha > 0.0:
            alpha -= 0.1
            self.attributes("-alpha", alpha)
            self.after(20, self.animate_out, alpha)
        else:
            self.destroy()

class SpotlightUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Shadow Automator Spotlight")
        self.geometry("750x80")
        
        # Center window on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (750 / 2)
        y = (screen_height / 4)
        self.geometry(f"750x80+{int(x)}+{int(y)}")
        
        # Frameless and translucent glassmorphism
        self.overrideredirect(True)
        self.attributes("-alpha", 0.95)
        self.attributes("-topmost", True)
        
        # Modern Theme colors (Tailwind Slate/Blue)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color="#0f172a") 
        
        # Inner Container for styling
        self.container = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=20, border_width=2, border_color="#3b82f6")
        self.container.pack(fill="both", expand=True, padx=4, pady=4)
        
        # Search Entry
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.container, 
            textvariable=self.search_var,
            width=700,
            height=50,
            font=("Segoe UI", 24),
            placeholder_text="✨ Ask Automator to click or type something...",
            placeholder_text_color="#64748b",
            corner_radius=15,
            border_width=0,
            fg_color="#1e293b",
            text_color="#38bdf8"
        )
        self.search_entry.pack(pady=10, padx=15)
        
        # Animated Progress Bar (Hidden by default)
        self.progress_bar = ctk.CTkProgressBar(
            self.container, 
            width=700, 
            height=4, 
            progress_color="#06b6d4", 
            fg_color="#1e293b",
            mode="indeterminate"
        )
        
        # Bindings
        self.bind("<Escape>", lambda e: self.hide_spotlight())
        self.search_entry.bind("<Return>", self.on_execute)
        
        self.is_visible = True
        self.is_processing = False

    def on_execute(self, event):
        query = self.search_var.get()
        if not query or self.is_processing:
            return
            
        print(f"[Spotlight] Executing: {query}")
        self.is_processing = True
        self.search_entry.configure(state="disabled", text_color="#94a3b8")
        
        # Expand window dynamically and show progress bar
        self.geometry(f"750x95")
        self.progress_bar.pack(side="bottom", pady=(0, 6))
        self.progress_bar.start()
        
        # Event Bus Trigger -> Orchestrator (Phase 3 Integration)
        threading.Thread(target=self.mock_orchestrator_job, args=(query,), daemon=True).start()

    def mock_orchestrator_job(self, query):
        """Simulates AI model inference and execution."""
        # Simulate LLM processing time
        time.sleep(2.0) 
        
        # Dispatch completion back to main thread
        self.after(0, self.finish_execution, query)

    def finish_execution(self, query):
        # Reset UI
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.geometry(f"750x80")
        self.search_entry.configure(state="normal", text_color="#38bdf8")
        self.search_var.set("")
        self.is_processing = False
        
        # Hide the spotlight and show success toast!
        self.hide_spotlight()
        ToastNotification(self, f"✅ Executed: '{query[:20]}...' | ROI: +$1.26", color="#10b981")

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
    keyboard.add_hotkey('ctrl+space', app.toggle_spotlight)
    keyboard.wait()

if __name__ == "__main__":
    app = SpotlightUI()
    listener_thread = threading.Thread(target=hotkey_listener, args=(app,), daemon=True)
    listener_thread.start()
    app.mainloop()
