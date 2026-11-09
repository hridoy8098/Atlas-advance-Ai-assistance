# backend/security/fake_screen.py — fullscreen decoy overlay (tkinter, background thread)

import threading
import time


class FakeScreen:
    def __init__(self):
        self._lock = threading.Lock()
        self._root = None
        self._thread = None
        self._visible = False

    def show(self, message: str = "Installing updates... 43%"):
        with self._lock:
            if self._visible:
                return {"visible": True, "note": "already shown"}
            try:
                import tkinter  # noqa: F401
            except Exception as e:
                return {"visible": False, "error": f"tkinter unavailable: {e}"}
            self._visible = True
            thread = threading.Thread(target=self._run, args=(message,), daemon=True)
            self._thread = thread
            thread.start()
        return {"visible": True, "note": "overlay started"}

    def hide(self):
        with self._lock:
            root = self._root
        if root is None:
            return {"visible": False, "note": "not shown"}
        try:
            root.after(0, root.destroy)
        except Exception:
            pass
        self._visible = False
        self._root = None
        return {"visible": False, "note": "overlay closed"}

    def is_visible(self):
        return self._visible

    def _run(self, message):
        try:
            import tkinter as tk

            root = tk.Tk()
            self._root = root
            root.configure(bg="#05070d")
            root.attributes("-fullscreen", True)
            root.attributes("-topmost", True)
            root.title("System")

            tk.Label(root, text=message, fg="#d0d6e2", bg="#05070d",
                     font=("Segoe UI", 26)).pack(expand=True)
            clock = tk.Label(root, text="", fg="#4a5568", bg="#05070d", font=("Consolas", 14))
            clock.pack(side="bottom", pady=30)

            def tick():
                clock.configure(text=time.strftime("%H:%M:%S"))
                root.after(1000, tick)

            tick()
            root.mainloop()
        except Exception as e:
            print(f"⚠️ FakeScreen error: {e}")
        finally:
            self._visible = False
            self._root = None


fake_screen = FakeScreen()
