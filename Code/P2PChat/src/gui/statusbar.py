import customtkinter as ctk

class StatusBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        # Set Corner_radius=0 to make the frame square and closely follow the bottom edge. Set Corner_radius=0 to make the frame square and closely follow the bottom edge.
        super().__init__(master, height=30, corner_radius=0, fg_color="#11111b", **kwargs)
        
        self.label = ctk.CTkLabel(
            self, 
            text="🔄 Initializing...", 
            text_color="#6c7086", 
            font=("Consolas", 12)
        )
        self.label.pack(side="left", padx=10)

    def set_status(self, text, color="#6c7086"):
        """This is a public function that other files can call when they need to change the message."""
        self.label.configure(text=text, text_color=color)