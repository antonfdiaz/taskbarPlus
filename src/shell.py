import os
import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import win32api
import win32con
import win32gui
import win32process
import psutil
from ctypes import windll

DWMWA_CLOAKED = 14

_dwmapi = getattr(ctypes.windll,"dwmapi",None)
_user32 = ctypes.windll.user32

def get_app_icon(path,size=26):
    provider = QFileIconProvider()
    icon = provider.icon(QFileInfo(path))
    pixmap = icon.pixmap(size,size)
    return QIcon(pixmap)

def _is_cloaked(hwnd):
    if _dwmapi is None:
        return False

    cloaked = wintypes.DWORD()
    result = _dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        wintypes.DWORD(DWMWA_CLOAKED),
        ctypes.byref(cloaked),
        ctypes.sizeof(cloaked),
    )
    return result == 0 and bool(cloaked.value)

def _should_include_window(hwnd,title,exe):
    if not title or not win32gui.IsWindowVisible(hwnd) or _is_cloaked(hwnd):
        return False

    if win32gui.GetParent(hwnd) != 0:
        return False

    ex_style = win32gui.GetWindowLong(hwnd,win32con.GWL_EXSTYLE)
    if ex_style & win32con.WS_EX_TOOLWINDOW:
        return False

    if ex_style & win32con.WS_EX_NOACTIVATE:
        return False

    root_owner = _user32.GetAncestor(wintypes.HWND(hwnd), wintypes.UINT(win32con.GA_ROOTOWNER))
    candidate = hwnd

    while True:
        last_popup = _user32.GetLastActivePopup(wintypes.HWND(candidate))
        if last_popup == candidate:
            break

        popup_title = win32gui.GetWindowText(last_popup).strip()
        if popup_title and win32gui.IsWindowVisible(last_popup) and not _is_cloaked(last_popup):
            candidate = last_popup
            break

        candidate = last_popup

    if candidate != hwnd and not (ex_style & win32con.WS_EX_APPWINDOW):
        return False

    if root_owner != hwnd and not (ex_style & win32con.WS_EX_APPWINDOW):
        return False

    exe_name = os.path.basename(exe).lower()

    ignored = {
        "textinputhost.exe",
        "shellexperiencehost.exe",
        "searchhost.exe",
        "startmenuexperiencehost.exe",
        "applicationframehost.exe",
        "lockapp.exe"
    }

    if exe_name in ignored:
        return False

    return True

def list_open_windows():
    windows = []
    seen_paths = set()

    def callback(hwnd,_):
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return

        try:
            _,pid = win32process.GetWindowThreadProcessId(hwnd)
            exe = psutil.Process(pid).exe()
        except (psutil.NoSuchProcess,psutil.AccessDenied,psutil.ZombieProcess):
            return

        if not _should_include_window(hwnd,title,exe):
            return

        key = (exe.lower(),hwnd)
        if key in seen_paths:
            return
        seen_paths.add(key)

        windows.append({
            "hwnd": hwnd,
            "pid": pid,
            "title": title,
            "path": exe,
        })

    win32gui.EnumWindows(callback,None)
    return windows

def press_key(vk: int):
    win32api.keybd_event(vk,0,0,0)

def release_key(vk: int):
    win32api.keybd_event(vk,0,win32con.KEYEVENTF_KEYUP,0)

def tap_key(vk: int):
    press_key(vk)
    release_key(vk)

def hide_taskbar():
    win32gui.ShowWindow(win32gui.FindWindow("Shell_TrayWnd",None),win32con.SW_HIDE)

def show_taskbar():
    win32gui.ShowWindow(win32gui.FindWindow("Shell_TrayWnd",None),win32con.SW_SHOW)

def launch_windows_app(target: str):
    result = windll.shell32.ShellExecuteW(None,"open",target,None,None,win32con.SW_SHOWNORMAL)
    if result <= 32:
        raise OSError(f"ShellExecuteW failed for {target!r} with code {result}")