import customtkinter as ctk
from datetime import datetime

def add_chat_bubble(scrollable_frame, message, is_me=True):
    """
    Create chat bubbles with integrated automatic time settings.
    - scrollable_frame: Main chat frame (CTkScrollableFrame)
    - message: Message content
    - is_me: True (self sent, right-aligned), False (other sent, left-aligned)
    """
    # 1. Set color and alignment
    if is_me:
        bg_color = "#89b4fa"      # pastel blue background
        text_color = "#11111b"    # black text
        time_color = "#45475a"    # dark gray time
        align = "e"               # right align
    else:
        bg_color = "#313145"      # dark gray background
        text_color = "#cdd6f4"    # white text
        time_color = "#a6adc8"    # light gray time
        align = "w"               # left align

    # 2. Create hidden frame to hold position (1 line of chat)
    row_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
    row_frame.pack(fill="x", pady=5, padx=10)

    # 3. Create chat bubble (Frame with rounded corners)
    bubble = ctk.CTkFrame(row_frame, fg_color=bg_color, corner_radius=15)
    bubble.pack(anchor=align)

    # 4. Insert message content
    text_label = ctk.CTkLabel(
        bubble, 
        text=message, 
        text_color=text_color,
        font=("Consolas", 13),
        wraplength=350,  # Force text to wrap to next line
        justify="left"
    )
    text_label.pack(padx=15, pady=(10, 0), anchor="w") 

    # 5. Insert time at the bottom corner
    current_time = datetime.now().strftime("%H:%M")
    time_label = ctk.CTkLabel(
        bubble, 
        text=current_time, 
        text_color=time_color,
        font=("Consolas", 10, "italic")
    )
    time_label.pack(padx=15, pady=(0, 6), anchor="e")