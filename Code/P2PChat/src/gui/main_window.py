import customtkinter as ctk
import threading
import time
from gui.sidebar import Sidebar
from gui.statusbar import StatusBar

# Set up standard dark mode interface
ctk.set_appearance_mode("dark")

class ChatApp(ctk.CTk):
    def __init__(self, listen_port=12000):
        super().__init__()
        self.title(f"💬 P2P Chat v2.0 (Port: {listen_port})")
        self.geometry("900x650")
        self.minsize(700, 500)
        self.listen_port = listen_port

        # --- Set up Responsive Grid ---
        # Column 0 (Chat) will expand (weight=1), Column 1 (Sidebar) stays fixed (weight=0)
        self.grid_columnconfigure(0, weight=1)  
        self.grid_columnconfigure(1, weight=0)  
        self.grid_rowconfigure(0, weight=1)     # main content row expands
        self.grid_rowconfigure(1, weight=0)     # Status bar row stays fixed

        self._build_ui()

    def _build_ui(self):
        # ================= LEFT AREA (MAIN CHAT) =================
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#1e1e2e")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1) # Chat box expands automatically

        # 1. Connection bar (UX Non-tech: Hides IP/Port)
        self.top_bar = ctk.CTkFrame(self.main_frame, height=50, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))

        self.nick_entry = ctk.CTkEntry(self.top_bar, placeholder_text="Enter nickname...", width=150, font=("Consolas", 12))
        self.nick_entry.pack(side="left", padx=(0, 10))

        self.connect_btn = ctk.CTkButton(
            self.top_bar, text="🔗 Start Chat", 
            font=("Consolas", 12, "bold"), fg_color="#89b4fa", text_color="#11111b",
            command=self._start_connect_thread # Call the function to start connection in a new thread
        )
        self.connect_btn.pack(side="left")

        # 2. Chat box (Disabled until conected)
        self.chat_box = ctk.CTkTextbox(
            self.main_frame, state="disabled", wrap="word", 
            font=("Consolas", 13), fg_color="#181825", text_color="#cdd6f4"
        )
        self.chat_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # 3. Message input area (Disabled by default)
        self.input_frame = ctk.CTkFrame(self.main_frame, height=50, fg_color="transparent")
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.msg_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Enter message...", state="disabled", font=("Consolas", 13))
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.send_btn = ctk.CTkButton(
            self.input_frame, text="▶ Send", width=80, state="disabled",
            font=("Consolas", 12, "bold"), fg_color="#a6e3a1", text_color="#11111b"
        )
        self.send_btn.pack(side="left")

        # ================= LEFT AREA (SIDEBAR) =================
        self.sidebar = Sidebar(self)
        self.sidebar.grid(row=0, column=1, sticky="ns")

        # ================= BOTTOM AREA (STATUS BAR) =================
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

    # ================= Logic (preventing GUI freeze)=================
    def _start_connect_thread(self):
        """Start a separate network thread to avoid freezing the interface."""
        # Lock the button to prevent multiple clicks.
        self.connect_btn.configure(state="disabled")
        self.status_bar.set_status("⏳ Setting up P2P network...", "#f9e2af")
        
        # Move the network waiting process to a different thread.
        threading.Thread(target=self._network_connect_task, daemon=True).start()

    def _network_connect_task(self):
        """Simulating socket handling functions (Running in the background)"""
        # TODO: Place the actual socket.bind() or socket.connect() code here.
        time.sleep(1.5) # Simulate 1.5s delay to open port
        
        # After the network is ready, request the main thread to update the UI
        self.after(0, self._on_connected)

    def _on_connected(self):
        """Update UI after the network is ready"""
        self.status_bar.set_status("✅ Ready to send and receive messages", "#a6e3a1")
        
        # Change the connect button to a disconnect button
        self.connect_btn.configure(
            text="✂️ Disconnect", state="normal", 
            fg_color="#f38ba8", hover_color="#d76f8c"
        )
        
        # Unlock message input field (clear UX)
        self.msg_entry.configure(state="normal")
        self.send_btn.configure(state="normal")

        # Simulate loading a list of peers to display in the sidebar.
        self.sidebar.update_peers(["James", "Alice"])

if __name__ == "__main__":
    app = ChatApp()
    app.mainloop()