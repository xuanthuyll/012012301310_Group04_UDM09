from __future__ import annotations

import threading
from collections import deque
from datetime import datetime
from typing import Deque

import tkinter as tk
import customtkinter as ctk

_TAG_SENT     = "sent"
_TAG_RECEIVED = "received"
_TAG_SYSTEM   = "system"
_TAG_LABEL    = "label"
_TAG_TIME     = "time"
_TAG_SEP      = "sep"

# A pending item is a plain tuple whose first element is the kind string.
_Item = tuple


class ChatBox(ctk.CTkFrame):
    """Thread-safe, colour-coded, batched-render chat display widget."""

    # Lifecycle #
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- render queue ------------------------------------------------
        self._queue: Deque[_Item] = deque()
        self._flush_lock  = threading.Lock()
        self._flush_sched = False          # True ⟺ an after(0,_flush) is queued

        self._setup_textbox()
        self._setup_tags()

    def _setup_textbox(self) -> None:
        self._tb_widget = ctk.CTkTextbox(
            self,
            wrap="word",
            corner_radius=8,
            state="disabled",
            cursor="arrow",
        )
        self._tb_widget.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

    def _setup_tags(self) -> None:
        raw: tk.Text = self._tb_widget._textbox

        raw.tag_configure(
            _TAG_SENT,
            foreground="#4FC3F7",
            justify="right",
            spacing1=2,
            spacing3=2,
        )
        raw.tag_configure(
            _TAG_RECEIVED,
            foreground="#A5D6A7",
            justify="left",
            spacing1=2,
            spacing3=2,
        )
        raw.tag_configure(
            _TAG_SYSTEM,
            foreground="#90A4AE",
            justify="center",
            spacing1=1,
            spacing3=1,
        )
        raw.tag_configure(_TAG_LABEL, font=("Consolas", 10, "bold"))
        raw.tag_configure(_TAG_TIME,  foreground="#546E7A", font=("Consolas", 8))
        raw.tag_configure(_TAG_SEP,   foreground="#37474F")

    # ------------------------------------------------------------------ #
    # Public API — thread-safe #
    def add_sent(self, sender: str, recipient: str, message: str) -> None:
        """Enqueue an outgoing message bubble."""
        self._enqueue(("sent", sender, recipient, message))

    def add_received(self, sender: str, message: str) -> None:
        """Enqueue an incoming message bubble."""
        self._enqueue(("received", sender, message))

    def add_system(self, text: str) -> None:
        """Enqueue a system / status line."""
        self._enqueue(("system", text))

    def clear(self) -> None:
        """Enqueue a clear-all operation."""
        self._enqueue(("clear",))

    # ------------------------------------------------------------------ #
    # Queue management #
    def _enqueue(self, item: _Item) -> None:
        """Append *item* to the render queue and request a flush."""
        self._queue.append(item)
        self._request_flush()

    def _request_flush(self) -> None:
        """Schedule exactly one flush on the Tk main thread.

        Uses a lock so that even if many threads call _request_flush
        simultaneously only a single after(0, _flush) is registered.
        """
        with self._flush_lock:

            if self._flush_sched:
                return          # flush already on its way
            
            self._flush_sched = True

        # after() is thread-safe in Tkinter — safe to call from any thread.
        self.after(0, self._flush)

    # ------------------------------------------------------------------ #
    # Batch flush — runs exclusively on the Tk main thread #

    def _flush(self) -> None:
        """Drain the entire queue in one Tk batch.

        Only one state("normal") / state("disabled") toggle happens per
        flush, keeping the widget fast even under rapid message bursts.
        """
        # Clear the scheduled flag *before* draining so that any messages
        # enqueued while we are rendering will trigger a new flush.
        with self._flush_lock:
            self._flush_sched = False

        if not self._queue:
            return

        raw: tk.Text = self._tb_widget._textbox
        at_bottom = _is_at_bottom(raw)

        self._tb_widget.configure(state="normal")
        try:

            while self._queue:

                item = self._queue.popleft()
                kind = item[0]

                if kind == "sent":
                    _render_sent(raw, item[1], item[2], item[3])

                elif kind == "received":
                    _render_received(raw, item[1], item[2])

                elif kind == "system":
                    _render_system(raw, item[1])

                elif kind == "clear":
                    raw.delete("1.0", "end")
        finally:
            self._tb_widget.configure(state="disabled")

        if at_bottom:
            raw.see("end")


# ─── module-level render helpers (no self dependency) ─────────────────────────
def _render_sent(raw, sender: str, recipient: str, message: str) -> None:
    ts = _now()
    raw.insert("end", f"  {sender} → {recipient}  ", (_TAG_SENT, _TAG_LABEL))
    raw.insert("end", f"{ts}\n",                      (_TAG_SENT, _TAG_TIME))
    raw.insert("end", f"  {message}\n\n",              _TAG_SENT)

def _render_received(raw, sender: str, message: str) -> None:
    ts = _now()
    raw.insert("end", f"  {sender}  ",    (_TAG_RECEIVED, _TAG_LABEL))
    raw.insert("end", f"{ts}\n",           (_TAG_RECEIVED, _TAG_TIME))
    raw.insert("end", f"  {message}\n\n",  _TAG_RECEIVED)

def _render_system(raw, text: str) -> None:
    ts = _now()
    raw.insert("end", f"  ── {ts} ",  (_TAG_SYSTEM, _TAG_TIME))
    raw.insert("end", f"{text}",       _TAG_SYSTEM)
    raw.insert("end", " ──\n\n",      (_TAG_SYSTEM, _TAG_SEP))

def _is_at_bottom(raw) -> bool:
    """True when the viewport bottom is within 5 % of the document end."""
    try:
        return raw.yview()[1] >= 0.95
    
    except Exception:
        return True

def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")
