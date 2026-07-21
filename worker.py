import ctypes
from ctypes import wintypes
import time
import os
import sys
import json
import threading
import subprocess

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32

# --- Win32 Constants ---
WM_HOTKEY = 0x0312
WM_USER = 0x0400
WM_RELOAD_CONFIG = WM_USER + 1
WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_RBUTTONUP = 0x0205
WM_LBUTTONDBLCLK = 0x0203

HOTKEY_ID = 1
APP_SYSTRAY_ID = 1001
APP_WM_ICONNOTIFY = WM_USER + 2

MENU_CONFIG = 101
MENU_EXIT = 102

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2

NIF_MESSAGE = 1
NIF_ICON = 2
NIF_TIP = 4

# --- Structs ---
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class INPUT_U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", ctypes.c_byte * 24), ("hi", ctypes.c_byte * 24)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", INPUT_U)]

class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HICON)
    ]

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HICON),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON)
    ]

# --- Config & Mapping ---
VK_MAPPING = {
    "tab": 0x09, "space": 0x20, "enter": 0x0D, "esc": 0x1B, 
    "backspace": 0x08, "pause": 0x13, "caps lock": 0x14,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "page up": 0x21, "page down": 0x22,
}
for i in range(26): VK_MAPPING[chr(ord('a') + i)] = 0x41 + i
for i in range(10): VK_MAPPING[str(i)] = 0x30 + i

CONFIG_FILE = "config.json"
BASE_DIR = os.path.dirname(sys.argv[0])

def get_config():
    config_path = os.path.join(BASE_DIR, CONFIG_FILE)
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
            if "hotkey" in data:
                return data["hotkey"]
    except Exception:
        pass
    return ["Ctrl", "Win"]

def parse_hotkey(hotkey_list):
    mods = 0
    vk = 0
    for key in hotkey_list:
        k = key.lower()
        if k in ("ctrl", "left ctrl", "right ctrl"): mods |= MOD_CONTROL
        elif k in ("alt", "left alt", "right alt"): mods |= MOD_ALT
        elif k in ("shift", "left shift", "right shift"): mods |= MOD_SHIFT
        elif k in ("win", "windows", "left windows", "right windows"): mods |= MOD_WIN
        else:
            vk = VK_MAPPING.get(k, 0)
            if vk == 0 and len(k) == 1:
                vk = ord(k.upper())
    return mods, vk

# --- Native Keyboard Simulation ---
def send_key(vk, scan, is_down):
    flags = 0
    if not is_down: flags |= KEYEVENTF_KEYUP
    
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki = KEYBDINPUT(vk, scan, flags, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def send_ctrl_c():
    send_key(0x11, 29, True)  # Ctrl down
    send_key(0x43, 46, True)  # C down
    time.sleep(0.01)
    send_key(0x43, 46, False) # C up
    send_key(0x11, 29, False) # Ctrl up

def send_ctrl_v():
    send_key(0x11, 29, True)  # Ctrl down
    send_key(0x56, 47, True)  # V down
    time.sleep(0.01)
    send_key(0x56, 47, False) # V up
    send_key(0x11, 29, False) # Ctrl up

def send_backspace():
    send_key(0x08, 14, True)
    send_key(0x08, 14, False)

def get_clipboard_text():
    if not user32.OpenClipboard(None): return ""
    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT): return ""
        h_data = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_data: return ""
        p_data = kernel32.GlobalLock(h_data)
        if not p_data: return ""
        text = ctypes.c_wchar_p(p_data).value
        kernel32.GlobalUnlock(h_data)
        return text
    finally:
        user32.CloseClipboard()

def set_clipboard_text(text):
    if not user32.OpenClipboard(None): return
    try:
        user32.EmptyClipboard()
        size = (len(text) + 1) * ctypes.sizeof(ctypes.c_wchar)
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, size)
        if not h_mem: return
        p_mem = kernel32.GlobalLock(h_mem)
        if p_mem:
            ctypes.memmove(p_mem, text, size)
            kernel32.GlobalUnlock(h_mem)
            user32.SetClipboardData(CF_UNICODETEXT, h_mem)
    finally:
        user32.CloseClipboard()

# --- Logic ---
layout_en = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
layout_ru = "йцукенгшщзхъфывапролджэячсмитьбю.ё"
en_to_ru = dict(zip(layout_en + layout_en.upper() + "@#$^&", layout_ru + layout_ru.upper() + '"№;:?'))
ru_to_en = dict(zip(layout_ru + layout_ru.upper() + '№', layout_en + layout_en.upper() + '#'))

def convert_text(text):
    if any(c in layout_ru or c in layout_ru.upper() for c in text):
        return ''.join(ru_to_en.get(c, c) for c in text)
    else:
        return ''.join(en_to_ru.get(c, c) for c in text)

def replace_text_action():
    original_clipboard = get_clipboard_text()
    
    send_ctrl_c()
    time.sleep(0.05)
    
    selected_text = get_clipboard_text()
    if not selected_text or selected_text == original_clipboard:
        # Restore clipboard if nothing selected
        set_clipboard_text(original_clipboard)
        return

    new_text = convert_text(selected_text)
    set_clipboard_text(new_text)
    time.sleep(0.05)
    send_ctrl_v()
    time.sleep(0.1)
    
    if original_clipboard:
        set_clipboard_text(original_clipboard)
    else:
        if user32.OpenClipboard(None):
            user32.EmptyClipboard()
            user32.CloseClipboard()

# --- IPC and Hotkey Management ---
main_thread_id = None

def register_current_hotkey():
    user32.UnregisterHotKey(None, HOTKEY_ID)
    selected_hotkey = get_config()
    mods, vk = parse_hotkey(selected_hotkey)
    if vk != 0:
        user32.RegisterHotKey(None, HOTKEY_ID, mods, vk)

# --- Tray Icon ---
def open_config():
    config_exe = os.path.join(BASE_DIR, "ReTypeConfig.exe")
    if os.path.exists(config_exe):
        subprocess.Popen([config_exe], creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        config_py = os.path.join(BASE_DIR, "config.py")
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw): pythonw = sys.executable
        subprocess.Popen([pythonw, config_py], creationflags=subprocess.CREATE_NO_WINDOW)

def wnd_proc(hwnd, msg, wparam, lparam):
    if msg == APP_WM_ICONNOTIFY:
        if lparam == WM_RBUTTONUP:
            # Show context menu
            menu = user32.CreatePopupMenu()
            user32.InsertMenuW(menu, 0, 0, MENU_CONFIG, "⚙ Open Config")
            user32.InsertMenuW(menu, 1, 0, MENU_EXIT, "❌ Exit ReType")
            
            pt = POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            user32.SetForegroundWindow(hwnd)
            
            cmd = user32.TrackPopupMenu(menu, 0x0100 | 0x0002, pt.x, pt.y, 0, hwnd, None)
            user32.DestroyMenu(menu)
            
            if cmd == MENU_CONFIG:
                open_config()
            elif cmd == MENU_EXIT:
                user32.PostQuitMessage(0)
        elif lparam == WM_LBUTTONDBLCLK:
            open_config()
        return 0
    elif msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

def setup_tray():
    wnd_class = WNDCLASSEXW()
    wnd_class.cbSize = ctypes.sizeof(WNDCLASSEXW)
    wnd_class.lpfnWndProc = WNDPROC(wnd_proc)
    wnd_class.hInstance = kernel32.GetModuleHandleW(None)
    wnd_class.lpszClassName = "ReTypeTrayClass"
    user32.RegisterClassExW(ctypes.byref(wnd_class))
    
    hwnd = user32.CreateWindowExW(0, "ReTypeTrayClass", "ReType Hidden", 0, 0, 0, 0, 0, 0, 0, wnd_class.hInstance, None)
    
    # Try to load a standard system icon if we don't have our own compiled resource
    hicon = user32.LoadIconW(0, 32512) # IDI_APPLICATION
    
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = APP_SYSTRAY_ID
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = APP_WM_ICONNOTIFY
    nid.hIcon = hicon
    nid.szTip = "ReType Background Process"
    
    shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
    return hwnd, nid

def cleanup_tray(nid):
    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))

def main():
    global main_thread_id
    main_thread_id = kernel32.GetCurrentThreadId()
    
    # Mutex for single instance
    mutex = kernel32.CreateMutexW(None, False, "ReTypeWorkerMutex_Unique")
    if kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        return # Another instance is running
    
    register_current_hotkey()
    hwnd, nid = setup_tray()
    
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
            threading.Thread(target=replace_text_action, daemon=True).start()
        elif msg.message == WM_RELOAD_CONFIG:
            register_current_hotkey()
        
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
        
    cleanup_tray(nid)

if __name__ == "__main__":
    main()
