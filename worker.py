import time
import threading
import json
import ctypes
from ctypes import wintypes
import keyboard
import pyperclip
import os
import sys

CONFIG_FILE = "config.json"

EN_CHARS = '''`qwertyuiop[]asdfghjkl;'zxcvbnm,./~QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?@#$^&'''
RU_CHARS = '''ёйцукенгшщзхъфывапролджэячсмитьбю.ЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ.,"№;:?'''
TRANS_DICT = {}
for e, r in zip(EN_CHARS, RU_CHARS):
    TRANS_DICT[e] = r
    TRANS_DICT[r] = e

def switch_layout(text):
    return "".join(TRANS_DICT.get(c, c) for c in text)

def force_release_modifiers():
    try:
        keyboard.release('ctrl')
        keyboard.release('shift')
        keyboard.release('alt')
        keyboard.release('windows')
    except Exception:
        pass

def safe_ctrl_c():
    keyboard.press('ctrl')
    keyboard.press(46) # C
    time.sleep(0.02)
    keyboard.release(46)
    keyboard.release('ctrl')

def safe_ctrl_v():
    keyboard.press('ctrl')
    keyboard.press(47) # V
    time.sleep(0.02)
    keyboard.release(47)
    keyboard.release('ctrl')

def safe_ctrl_shift_left():
    keyboard.press('ctrl')
    keyboard.press('shift')
    keyboard.press('left')
    time.sleep(0.02)
    keyboard.release('left')
    keyboard.release('shift')
    keyboard.release('ctrl')

def replace_text_action():
    time.sleep(0.1)
    force_release_modifiers()
    time.sleep(0.1)
        
    try:
        original_clipboard = pyperclip.paste()
    except Exception:
        original_clipboard = ""
        
    pyperclip.copy("")
    
    safe_ctrl_c()
    time.sleep(0.1)
    
    copied_text = pyperclip.paste()
    
    if not copied_text:
        safe_ctrl_shift_left()
        time.sleep(0.1)
        pyperclip.copy("")
        safe_ctrl_c()
        time.sleep(0.1)
        copied_text = pyperclip.paste()
        
    if copied_text:
        new_text = switch_layout(copied_text)
        pyperclip.copy(new_text)
        time.sleep(0.1)
        safe_ctrl_v()
        time.sleep(0.1)
        
    time.sleep(0.3)
    if original_clipboard != "":
        pyperclip.copy(original_clipboard)
    else:
        pyperclip.copy("")

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312
HOTKEY_ID = 1

VK_MAPPING = {
    "tab": 0x09, "space": 0x20, "enter": 0x0D, "esc": 0x1B, 
    "backspace": 0x08, "pause": 0x13, "caps lock": 0x14,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "page up": 0x21, "page down": 0x22,
}
for i in range(26): VK_MAPPING[chr(ord('a') + i)] = 0x41 + i
for i in range(10): VK_MAPPING[str(i)] = 0x30 + i
for i in range(1, 13): VK_MAPPING[f"f{i}"] = 0x6F + i
VK_MAPPING.update({'`': 0xC0, '-': 0xBD, '=': 0xBB, '[': 0xDB, ']': 0xDD, '\\': 0xDC, ';': 0xBA, "'": 0xDE, ',': 0xBC, '.': 0xBE, '/': 0xBF})

def parse_hotkey(keys):
    mods, vk = 0, 0
    for key in keys:
        k = key.lower()
        if k in ("ctrl", "left ctrl", "right ctrl"): mods |= MOD_CONTROL
        elif k in ("alt", "left alt", "right alt", "alt gr", "altgr"): mods |= MOD_ALT
        elif k in ("shift", "left shift", "right shift"): mods |= MOD_SHIFT
        elif k in ("win", "windows", "left windows", "right windows"): mods |= MOD_WIN
        else:
            vk = VK_MAPPING.get(k, 0)
            if vk == 0 and len(k) == 1: vk = ord(k.upper())
    return mods | 0x4000, vk

def get_config():
    config_path = os.path.join(os.path.dirname(sys.argv[0]), CONFIG_FILE)
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
            if "hotkey" in data:
                return data["hotkey"]
    except Exception:
        pass
    return ["Ctrl", "Win"]

def hotkey_loop():
    selected_hotkey = get_config()
    if not selected_hotkey:
        return
        
    mods, vk = parse_hotkey(selected_hotkey)
    user32 = ctypes.windll.user32
    if not user32.RegisterHotKey(None, HOTKEY_ID, mods, vk):
        print(f"Failed to register native hotkey mods={mods} vk={vk}")
        return
        
    msg = wintypes.MSG()
    while user32.GetMessageA(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
            threading.Thread(target=replace_text_action, daemon=True).start()
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageA(ctypes.byref(msg))

import pystray
from PIL import Image, ImageDraw
import subprocess

def create_image():
    image = Image.new('RGB', (64, 64), color=(30, 30, 30))
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=(0, 120, 215))
    dc.rectangle((24, 24, 40, 40), fill=(255, 255, 255))
    return image

def on_open_config(icon, item):
    base_dir = os.path.dirname(sys.argv[0])
    config_exe = os.path.join(base_dir, "ReTypeConfig.exe")
    if os.path.exists(config_exe):
        subprocess.Popen([config_exe], creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        config_py = os.path.join(base_dir, "config.py")
        if os.path.exists(config_py):
            pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pythonw): pythonw = sys.executable
            subprocess.Popen([pythonw, config_py], creationflags=subprocess.CREATE_NO_WINDOW)

def on_exit(icon, item):
    icon.stop()
    os._exit(0)

def main():
    # Start hotkey listener in background
    threading.Thread(target=hotkey_loop, daemon=True).start()
    
    # Run tray icon on main thread
    menu = pystray.Menu(
        pystray.MenuItem("⚙ Open Config", on_open_config, default=True),
        pystray.MenuItem("❌ Exit ReType", on_exit)
    )
    icon = pystray.Icon("ReType", create_image(), "ReType Background Process", menu)
    icon.run()

if __name__ == "__main__":
    main()
