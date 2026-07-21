import os
import sys
import customtkinter as ctk
import keyboard
import json
import webbrowser
import subprocess

try:
    import winreg
except ImportError:
    winreg = None

APP_NAME = "ReType"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

BASE_DIR = os.path.dirname(sys.argv[0])
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

editing_hotkey = False
selected_hotkey = ["Ctrl", "Win"]
current_lang = "RU"
hook_handle = None
active_hotkey = []
captured_hotkey = []

def get_worker_path():
    if getattr(sys, "frozen", False):
        return os.path.join(BASE_DIR, "ReTypeWorker.exe")
    return os.path.join(BASE_DIR, "worker.py")

def restart_worker():
    if getattr(sys, "frozen", False):
        subprocess.run(["taskkill", "/F", "/IM", "ReTypeWorker.exe"], capture_output=True)
        worker_path = get_worker_path()
        if os.path.exists(worker_path):
            subprocess.Popen([worker_path], creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        # In dev, we can restart it using pythonw
        subprocess.run(["taskkill", "/F", "/IM", "pythonw.exe"], capture_output=True)
        worker_path = get_worker_path()
        if os.path.exists(worker_path):
            pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if os.path.exists(pythonw):
                subprocess.Popen([pythonw, worker_path], creationflags=subprocess.CREATE_NO_WINDOW)

def load_config():
    global selected_hotkey, current_lang
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            if "hotkey" in data:
                selected_hotkey = data["hotkey"]
            if "lang" in data:
                current_lang = data["lang"]
    except Exception:
        pass

def save_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "hotkey": selected_hotkey,
                "lang": current_lang
            }, f)
        restart_worker()
    except Exception:
        pass

load_config()
restart_worker()

app = ctk.CTk()
app.resizable(False, False)
app.geometry("350x500")
app.title("ReType Config")

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

label_cfg = ctk.CTkLabel(
    app,
    text=TRANSLATIONS[current_lang]["config"],
    font=("Arial", 38, "bold")
)
label_cfg.place(x=18, y=18)

def change_language(new_lang):
    global current_lang
    current_lang = new_lang
    label_cfg.configure(text=TRANSLATIONS[current_lang]["config"])
    label_hk.configure(text=TRANSLATIONS[current_lang]["hotkey"])
    label_autostart.configure(text=TRANSLATIONS[current_lang]["autostart"])
    update_display_text()
    save_config()

lang_switch = ctk.CTkSegmentedButton(
    app, 
    values=["EN", "RU"], 
    command=change_language,
    width=80
)
lang_switch.place(x=250, y=25)
lang_switch.set(current_lang)

frame_hk = ctk.CTkFrame(
    app,
    width=330,
    height=60,
    corner_radius=14,
    fg_color="#2B2B2B",
    border_width=1,
    border_color="#444444"
)
frame_hk.place(x=10, y=75)

label_hk = ctk.CTkLabel(
    frame_hk,
    text=TRANSLATIONS[current_lang]["hotkey"],
    font=("Arial", 20, "bold"),
    fg_color="transparent"
)
label_hk.place(x=15, y=15)

frame_hk_display = ctk.CTkFrame(
    frame_hk,
    width=170,
    height=50,
    corner_radius=10,
    fg_color="#1B1B1B",
    border_width=1,
    border_color="#4A4A4A"
)
frame_hk_display.place(x=100, y=5)

hotkey_display = ctk.CTkLabel(
    frame_hk_display,
    text="",
    font=("Segoe UI", 16, "bold"),
    fg_color="transparent",
    text_color="#F2F2F2"
)
hotkey_display.place(relx=0.5, rely=0.5, anchor="center")

frame_autostart = ctk.CTkFrame(
    app,
    width=330,
    height=60,
    corner_radius=14,
    fg_color="#2B2B2B",
    border_width=1,
    border_color="#444444"
)
frame_autostart.place(x=10, y=145)

label_autostart = ctk.CTkLabel(
    frame_autostart,
    text=TRANSLATIONS[current_lang]["autostart"],
    font=("Arial", 20, "bold"),
    fg_color="transparent"
)
label_autostart.place(x=15, y=15)

def get_startup_command():
    worker_path = get_worker_path()
    if getattr(sys, "frozen", False):
        return f'"{worker_path}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    interpreter = pythonw if os.path.exists(pythonw) else sys.executable
    return f'"{interpreter}" "{worker_path}"'

def is_autostart_enabled():
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False

def set_autostart(enabled):
    if winreg is None:
        return
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
    except OSError:
        return
    if enabled:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_startup_command())
    else:
        try:
            winreg.DeleteValue(key, APP_NAME)
        except OSError:
            pass
    winreg.CloseKey(key)

def on_autostart_toggle():
    set_autostart(switch_autostart.get() == 1)

switch_autostart = ctk.CTkSwitch(
    frame_autostart,
    text="",
    command=on_autostart_toggle,
    onvalue=1,
    offvalue=0
)
switch_autostart.place(x=270, y=18)

if winreg is None:
    switch_autostart.configure(state="disabled")
elif is_autostart_enabled():
    switch_autostart.select()
else:
    switch_autostart.deselect()

def update_hotkey_ui():
    if editing_hotkey:
        frame_hk_display.configure(
            fg_color="#222222",
            border_color="#7A7A7A",
            border_width=2
        )
        btn_edit_hk.configure(
            fg_color="#5A5A5A",
            hover_color="#6C6C6C"
        )
    else:
        frame_hk_display.configure(
            fg_color="#1B1B1B",
            border_color="#4A4A4A",
            border_width=1
        )
        btn_edit_hk.configure(
            fg_color="#4A4A4A",
            hover_color="#626262"
        )
    hotkey_display.configure(text_color="#F2F2F2")

def update_display_text():
    if editing_hotkey:
        if active_hotkey:
            hotkey_display.configure(text="+".join(active_hotkey))
        else:
            hotkey_display.configure(text=TRANSLATIONS[current_lang]["press_keys"])
    else:
        hotkey_display.configure(text="+".join(selected_hotkey))

def normalize_key_name(raw_name):
    name = (raw_name or "").lower().strip()
    if name in {"left ctrl", "right ctrl", "ctrl"}:
        return "Ctrl"
    if name in {"left alt", "right alt", "alt"}:
        return "Alt"
    if name in {"alt gr", "altgr"}:
        return "AltGr"
    if name in {"left shift", "right shift", "shift"}:
        return "Shift"
    if name in {"left windows", "right windows", "windows"}:
        return "Win"
    if name == "esc":
        return "Esc"
    if name == "space":
        return "Space"
    if name == "enter":
        return "Enter"
    if len(name) == 1:
        return name.upper()
    return name.title()

def finish_hotkey(cancel=False):
    global editing_hotkey, selected_hotkey, active_hotkey, captured_hotkey, hook_handle
    editing_hotkey = False
    if hook_handle is not None:
        keyboard.unhook(hook_handle)
        hook_handle = None
    if not cancel and captured_hotkey:
        selected_hotkey = list(captured_hotkey)
        save_config()
    active_hotkey = []
    captured_hotkey = []
    update_display_text()
    update_hotkey_ui()

def process_keyboard_event(raw_name, event_type):
    global active_hotkey, captured_hotkey
    if not editing_hotkey:
        return
    name = normalize_key_name(raw_name)

    if event_type == "down":
        if name == "Esc":
            finish_hotkey(cancel=True)
            return
        if name not in active_hotkey:
            active_hotkey.append(name)
        for key in active_hotkey:
            if key not in captured_hotkey and len(captured_hotkey) < 3:
                captured_hotkey.append(key)
        update_display_text()
        update_hotkey_ui()
        if len(active_hotkey) >= 3:
            finish_hotkey()
    elif event_type == "up":
        if name in active_hotkey:
            active_hotkey.remove(name)
        update_display_text()
        update_hotkey_ui()
        if not active_hotkey and captured_hotkey:
            finish_hotkey()

def keyboard_event_handler(event):
    app.after(0, process_keyboard_event, event.name, event.event_type)

def btn_edit_hk_event():
    global editing_hotkey, active_hotkey, captured_hotkey, hook_handle
    if editing_hotkey:
        finish_hotkey()
        return
    editing_hotkey = True
    active_hotkey = []
    captured_hotkey = []
    update_display_text()
    update_hotkey_ui()

    hook_handle = keyboard.hook(keyboard_event_handler)

def on_close():
    try:
        keyboard.unhook_all()
    except Exception:
        pass
    app.destroy()

btn_edit_hk = ctk.CTkButton(
    frame_hk,
    text="✎",
    command=btn_edit_hk_event,
    font=("Segoe UI Symbol", 20),
    width=42,
    height=46,
    corner_radius=8,
    fg_color="#4A4A4A",
    hover_color="#626262",
    text_color="white"
)
btn_edit_hk.place(x=280, y=7)

version_label = ctk.CTkLabel(
    app, 
    text="ReType v1.0", 
    text_color="#888888", 
    font=("Arial", 12)
)
version_label.place(x=15, y=475, anchor="w")

def open_github(event):
    webbrowser.open_new("https://github.com/m1xamm/re-type")

github_label = ctk.CTkLabel(
    app, 
    text="GitHub", 
    text_color="#888888", 
    font=("Arial", 12, "underline"), 
    cursor="hand2"
)
github_label.place(x=335, y=475, anchor="e")
github_label.bind("<Button-1>", open_github)

app.protocol("WM_DELETE_WINDOW", on_close)

update_hotkey_ui()
update_display_text()

app.mainloop()
