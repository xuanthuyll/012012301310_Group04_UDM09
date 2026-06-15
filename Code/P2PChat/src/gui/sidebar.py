import customtkinter as ctk

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, width=200, corner_radius=0, fg_color="#181825", **kwargs)
    
        # Title
        self.title = ctk.CTkLabel(
            self, text="🌐 Peers", 
            font=("Consolas", 14, "bold"), text_color="#cdd6f4"
        )
        self.title.pack(pady=(15, 5), padx=10, anchor="w")

        # Scrollable frame for the list
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Info label below
        self.info_label = ctk.CTkLabel(
            self, text="── Select a peer ──", 
            text_color="#6c7086", font=("Consolas", 11)
        )
        self.info_label.pack(side="bottom", pady=15)

    def update_peers(self, peer_list):
        """Function to update the list of online peers"""
        # Remove existing peer widgets
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        # Add new peers
        for peer in peer_list:
            btn = ctk.CTkButton(
                self.scroll_frame, 
                text=peer, 
                fg_color="#313145", 
                hover_color="#45475a",
                anchor="w" # left align text
            )
            btn.pack(fill="x", pady=2)