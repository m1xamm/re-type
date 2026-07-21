import os
import sys
import json
import webbrowser
import subprocess
import threading
import ctypes
import customtkinter as ctk
import keyboard

try:
    import winreg
except ImportError:
    winreg = None

APP_NAME = "ReType"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
BASE_DIR = os.path.dirname(sys.argv[0])
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

WM_USER = 0x0400
WM_RELOAD_CONFIG = WM_USER + 1

TRANSLATIONS = {
    "EN": {
        "config": "Config",
        "hotkey": "Hotkey",
        "autostart": "Autostart",
        "press_keys": "Press keys..."
    },
    "RU": {
        "config": "Настройки",
        "hotkey": "Хоткей",
        "autostart": "Автозапуск",
        "press_keys": "Нажмите..."
    }
}

class ReTypeConfigApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("Dark")
        self.title("ReType Config")
        self.geometry("350x500")
        self.resizable(False, False)

        self.selected_hotkey = ["Ctrl", "Win"]
        self.current_lang = "RU"
        self.editing_hotkey = False
        self.active_hotkey = []
        self.captured_hotkey = []
        self.hook_handle = None

        self.load_config()
        self.trigger_worker()

        self.setup_ui()
        self.update_ui_language()
        self.update_hotkey_ui()
        self.update_display_text()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                self.selected_hotkey = data.get("hotkey", ["Ctrl", "Win"])
                self.current_lang = data.get("lang", "RU")
        except Exception:
            pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({
                    "hotkey": self.selected_hotkey,
                    "lang": self.current_lang
                }, f)
            self.trigger_worker()
        except Exception:
            pass

    def get_worker_path(self):
        if getattr(sys, "frozen", False):
            return os.path.join(BASE_DIR, "ReTypeWorker.exe")
        return os.path.join(BASE_DIR, "worker.py")

    def trigger_worker(self):
        # IPC: find worker window and send reload message
        hwnd = ctypes.windll.user32.FindWindowW("ReTypeTrayClass", None)
        if hwnd:
            ctypes.windll.user32.PostMessageW(hwnd, WM_RELOAD_CONFIG, 0, 0)
        else:
            # Start worker
            worker_path = self.get_worker_path()
            if os.path.exists(worker_path):
                if getattr(sys, "frozen", False):
                    subprocess.Popen([worker_path], creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                    if not os.path.exists(pythonw): pythonw = sys.executable
                    subprocess.Popen([pythonw, worker_path], creationflags=subprocess.CREATE_NO_WINDOW)

    def setup_ui(self):
        self.label_cfg = ctk.CTkLabel(self, text="", font=("Arial", 38, "bold"))
        self.label_cfg.place(x=18, y=18)

        self.lang_switch = ctk.CTkSegmentedButton(self, values=["EN", "RU"], command=self.change_language, width=80)
        self.lang_switch.place(x=250, y=25)
        self.lang_switch.set(self.current_lang)

        # Hotkey section
        self.frame_hk = ctk.CTkFrame(self, width=330, height=60, corner_radius=14, fg_color="#2B2B2B", border_width=1, border_color="#444444")
        self.frame_hk.place(x=10, y=75)

        self.label_hk = ctk.CTkLabel(self.frame_hk, text="", font=("Arial", 20, "bold"), fg_color="transparent")
        self.label_hk.place(x=15, y=15)

        self.frame_hk_display = ctk.CTkFrame(self.frame_hk, width=170, height=50, corner_radius=10, fg_color="#1B1B1B", border_width=1, border_color="#4A4A4A")
        self.frame_hk_display.place(x=100, y=5)

        self.hotkey_display = ctk.CTkLabel(self.frame_hk_display, text="", font=("Segoe UI", 16, "bold"), fg_color="transparent", text_color="#F2F2F2")
        self.hotkey_display.place(relx=0.5, rely=0.5, anchor="center")

        self.btn_edit_hk = ctk.CTkButton(self.frame_hk, text="✎", command=self.btn_edit_hk_event, font=("Segoe UI Symbol", 20), width=42, height=46, corner_radius=8, fg_color="#4A4A4A", hover_color="#626262", text_color="white")
        self.btn_edit_hk.place(x=280, y=7)

        # Autostart section
        self.frame_autostart = ctk.CTkFrame(self, width=330, height=60, corner_radius=14, fg_color="#2B2B2B", border_width=1, border_color="#444444")
        self.frame_autostart.place(x=10, y=145)

        self.label_autostart = ctk.CTkLabel(self.frame_autostart, text="", font=("Arial", 20, "bold"), fg_color="transparent")
        self.label_autostart.place(x=15, y=15)

        self.switch_autostart = ctk.CTkSwitch(self.frame_autostart, text="", command=self.on_autostart_toggle, onvalue=1, offvalue=0)
        self.switch_autostart.place(x=270, y=18)

        if winreg is None:
            self.switch_autostart.configure(state="disabled")
        elif self.is_autostart_enabled():
            self.switch_autostart.select()
        else:
            self.switch_autostart.deselect()

        # Footer
        self.version_label = ctk.CTkLabel(self, text="ReType v1.0", text_color="#888888", font=("Arial", 12))
        self.version_label.place(x=15, y=475, anchor="w")

        self.github_label = ctk.CTkLabel(self, text="GitHub", text_color="#888888", font=("Arial", 12, "underline"), cursor="hand2")
        self.github_label.place(x=335, y=475, anchor="e")
        self.github_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/m1xamm/re-type"))

    def change_language(self, new_lang):
        self.current_lang = new_lang
        self.update_ui_language()
        self.save_config()

    def update_ui_language(self):
        t = TRANSLATIONS[self.current_lang]
        self.label_cfg.configure(text=t["config"])
        self.label_hk.configure(text=t["hotkey"])
        self.label_autostart.configure(text=t["autostart"])
        self.update_display_text()

    def get_startup_command(self):
        worker_path = self.get_worker_path()
        if getattr(sys, "frozen", False):
            return f'"{worker_path}"'
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        interpreter = pythonw if os.path.exists(pythonw) else sys.executable
        return f'"{interpreter}" "{worker_path}"'

    def is_autostart_enabled(self):
        if winreg is None: return False
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except OSError:
            return False

    def on_autostart_toggle(self):
        if winreg is None: return
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
            if self.switch_autostart.get() == 1:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, self.get_startup_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except OSError:
                    pass
            winreg.CloseKey(key)
        except OSError:
            pass

    def update_hotkey_ui(self):
        if self.editing_hotkey:
            self.frame_hk_display.configure(fg_color="#222222", border_color="#7A7A7A", border_width=2)
            self.btn_edit_hk.configure(fg_color="#5A5A5A", hover_color="#6C6C6C")
        else:
            self.frame_hk_display.configure(fg_color="#1B1B1B", border_color="#4A4A4A", border_width=1)
            self.btn_edit_hk.configure(fg_color="#4A4A4A", hover_color="#626262")
        self.hotkey_display.configure(text_color="#F2F2F2")

    def update_display_text(self):
        if self.editing_hotkey:
            if self.active_hotkey:
                self.hotkey_display.configure(text="+".join(self.active_hotkey))
            else:
                self.hotkey_display.configure(text=TRANSLATIONS[self.current_lang]["press_keys"])
        else:
            self.hotkey_display.configure(text="+".join(self.selected_hotkey))

    def normalize_key_name(self, raw_name):
        name = (raw_name or "").lower().strip()
        if name in {"left ctrl", "right ctrl", "ctrl"}: return "Ctrl"
        if name in {"left alt", "right alt", "alt"}: return "Alt"
        if name in {"alt gr", "altgr"}: return "AltGr"
        if name in {"left shift", "right shift", "shift"}: return "Shift"
        if name in {"left windows", "right windows", "windows"}: return "Win"
        if name == "esc": return "Esc"
        if name == "space": return "Space"
        if name == "enter": return "Enter"
        if len(name) == 1: return name.upper()
        return name.title()

    def finish_hotkey(self, cancel=False):
        self.editing_hotkey = False
        if self.hook_handle is not None:
            keyboard.unhook(self.hook_handle)
            self.hook_handle = None
        if not cancel and self.captured_hotkey:
            self.selected_hotkey = list(self.captured_hotkey)
            self.save_config()
        self.active_hotkey = []
        self.captured_hotkey = []
        self.update_display_text()
        self.update_hotkey_ui()

    def process_keyboard_event(self, raw_name, event_type):
        if not self.editing_hotkey: return
        name = self.normalize_key_name(raw_name)

        if event_type == "down":
            if name == "Esc":
                self.finish_hotkey(cancel=True)
                return
            if name not in self.active_hotkey:
                self.active_hotkey.append(name)
            for key in self.active_hotkey:
                if key not in self.captured_hotkey and len(self.captured_hotkey) < 3:
                    self.captured_hotkey.append(key)
            self.update_display_text()
            self.update_hotkey_ui()
            if len(self.active_hotkey) >= 3:
                self.finish_hotkey()
        elif event_type == "up":
            if name in self.active_hotkey:
                self.active_hotkey.remove(name)
            self.update_display_text()
            self.update_hotkey_ui()
            if not self.active_hotkey and self.captured_hotkey:
                self.finish_hotkey()

    def keyboard_event_handler(self, event):
        self.after(0, self.process_keyboard_event, event.name, event.event_type)

    def btn_edit_hk_event(self):
        if self.editing_hotkey:
            self.finish_hotkey()
            return
        self.editing_hotkey = True
        self.active_hotkey = []
        self.captured_hotkey = []
        self.update_display_text()
        self.update_hotkey_ui()
        self.hook_handle = keyboard.hook(self.keyboard_event_handler)

    def on_close(self):
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.destroy()

if __name__ == "__main__":
    app = ReTypeConfigApp()
    app.mainloop()
