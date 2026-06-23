"""Runtime GUI Vyn — tkinter natif, reinitialisable."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable, Dict, Optional

_gui: Optional["VynGui"] = None


class VynGui:
    def __init__(self):
        self.root = tk.Tk()
        self.widgets: Dict[str, Any] = {}
        self._callbacks: Dict[str, Callable] = {}

    def window(self, title: str, width: int = 640, height: int = 480) -> None:
        self.root.title(title)
        self.root.geometry(f"{int(width)}x{int(height)}")
        self.root.configure(bg="#1e1e1e")

    def label(self, wid: str, text: str, x: int, y: int) -> None:
        lbl = tk.Label(
            self.root, text=str(text), bg="#1e1e1e", fg="#d4d4d4",
            font=("Segoe UI", 11),
        )
        lbl.place(x=int(x), y=int(y))
        self.widgets[wid] = lbl

    def button(self, wid: str, text: str, x: int, y: int, cb_id: str = "") -> None:
        def _click():
            cb = self._callbacks.get(cb_id)
            if cb:
                cb()

        btn = tk.Button(
            self.root, text=str(text), command=_click,
            bg="#0e639c", fg="white", font=("Segoe UI", 10),
            relief="flat", padx=12, pady=4,
        )
        btn.place(x=int(x), y=int(y))
        self.widgets[wid] = btn

    def set_callback(self, cb_id: str, fn: Callable) -> None:
        self._callbacks[cb_id] = fn

    def alert(self, msg: str) -> None:
        messagebox.showinfo("Vyn", str(msg))

    def run(self) -> None:
        try:
            self.root.mainloop()
        finally:
            try:
                self.root.destroy()
            except tk.TclError:
                pass


def reset_gui() -> None:
    """Detruit l'instance GUI — obligatoire entre deux executions."""
    global _gui
    if _gui is not None:
        try:
            _gui.root.destroy()
        except tk.TclError:
            pass
        _gui = None


def get_gui() -> VynGui:
    global _gui
    if _gui is None:
        _gui = VynGui()
    return _gui
