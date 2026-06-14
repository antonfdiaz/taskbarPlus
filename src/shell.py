import os
import ctypes
import time
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
START_MENU_PROCESS_NAMES = {
    "startmenuexperiencehost.exe",
    "searchapp.exe",
    "startmenu.exe" #open shell
}
START_MENU_TITLES = {"start","inicio","search","buscar"}
TB_GETBUTTON = win32con.WM_USER+23
TB_BUTTONCOUNT = win32con.WM_USER+24
TB_GETBUTTONTEXTW = win32con.WM_USER+75

PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04

_dwmapi = getattr(ctypes.windll,"dwmapi",None)
_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

ULONG_PTR = wintypes.WPARAM
LONG_PTR = wintypes.LPARAM

_user32.SendMessageW.argtypes = [wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
_user32.SendMessageW.restype = wintypes.LPARAM

if ctypes.sizeof(ctypes.c_void_p) == 8:
    _button_reserved = 6
else:
    _button_reserved = 2

class TBBUTTON(ctypes.Structure):
    _fields_ = [
        ("iBitmap",ctypes.c_int),
        ("idCommand",ctypes.c_int),
        ("fsState",ctypes.c_ubyte),
        ("fsStyle",ctypes.c_ubyte),
        ("bReserved",ctypes.c_ubyte*_button_reserved),
        ("dwData",ULONG_PTR),
        ("iString",LONG_PTR),
    ]

class TRAYDATA(ctypes.Structure):
    _fields_ = [
        ("hwnd",wintypes.HWND),
        ("uid",wintypes.UINT),
        ("callback_message",wintypes.UINT),
        ("reserved",wintypes.DWORD * 2),
        ("hicon",wintypes.HICON),
    ]

_kernel32.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.VirtualAllocEx.argtypes = [wintypes.HANDLE,wintypes.LPVOID,ctypes.c_size_t,wintypes.DWORD,wintypes.DWORD]
_kernel32.VirtualAllocEx.restype = wintypes.LPVOID
_kernel32.VirtualFreeEx.argtypes = [wintypes.HANDLE,wintypes.LPVOID,ctypes.c_size_t,wintypes.DWORD]
_kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE,wintypes.LPCVOID,wintypes.LPVOID,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
_kernel32.ReadProcessMemory.restype = wintypes.BOOL

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

def should_include_window(hwnd,title,exe):
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

def _raw_value(value):
    return value.value if hasattr(value,"value") else value

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

        if not should_include_window(hwnd,title,exe):
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

def _find_child_window(parent,class_name,direct=False):
    found = 0

    def callback(hwnd,_):
        nonlocal found
        if direct and win32gui.GetParent(hwnd) != parent:
            return True

        if win32gui.GetClassName(hwnd) == class_name:
            found = hwnd
            return False
        return True

    if parent:
        win32gui.EnumChildWindows(parent,callback,None)

    return found

def _find_child_windows(parent,class_name,direct=False):
    found = []

    def callback(hwnd,_):
        if direct and win32gui.GetParent(hwnd) != parent:
            return True

        if win32gui.GetClassName(hwnd) == class_name:
            found.append(hwnd)
        return True

    if parent:
        win32gui.EnumChildWindows(parent,callback,None)

    return found

def _append_unique_hwnds(target,items):
    for item in items:
        if item and item not in target:
            target.append(item)

def get_tray_toolbars():
    toolbars = []

    tray = win32gui.FindWindow("Shell_TrayWnd",None)
    tray_notify = _find_child_window(tray,"TrayNotifyWnd")
    sys_pager = _find_child_window(tray_notify,"SysPager")

    _append_unique_hwnds(toolbars,_find_child_windows(sys_pager,"ToolbarWindow32"))
    _append_unique_hwnds(toolbars,_find_child_windows(tray_notify,"ToolbarWindow32"))

    overflow = win32gui.FindWindow("NotifyIconOverflowWindow",None)
    _append_unique_hwnds(toolbars,_find_child_windows(overflow,"ToolbarWindow32"))

    return toolbars

def _read_process_memory(process,address,ctype):
    value = ctype()
    bytes_read = ctypes.c_size_t()
    address = _raw_value(address)
    ok = _kernel32.ReadProcessMemory(
        process,
        ctypes.c_void_p(address),
        ctypes.byref(value),
        ctypes.sizeof(value),
        ctypes.byref(bytes_read),
    )
    if not ok or bytes_read.value != ctypes.sizeof(value):
        return None
    return value

def _read_tray_button(process,toolbar_hwnd,index,remote_button):
    remote_address = _raw_value(remote_button)
    if not _user32.SendMessageW(toolbar_hwnd,TB_GETBUTTON,index,remote_address):
        return None
    return _read_process_memory(process,remote_button,TBBUTTON)

def _read_tray_tooltip(process,toolbar_hwnd,button):
    if not button.iString:
        return ""

    length = _user32.SendMessageW(toolbar_hwnd,TB_GETBUTTONTEXTW,button.idCommand,0)
    if length <= 0 or length > 512:
        return ""

    buffer_size = (length + 1) * ctypes.sizeof(wintypes.WCHAR)
    remote_text = _kernel32.VirtualAllocEx(process,None,buffer_size,MEM_COMMIT,PAGE_READWRITE)
    if not remote_text:
        return ""

    try:
        remote_address = _raw_value(remote_text)
        _user32.SendMessageW(toolbar_hwnd,TB_GETBUTTONTEXTW,button.idCommand,remote_address)
        text_buffer = ctypes.create_unicode_buffer(length + 1)
        bytes_read = ctypes.c_size_t()
        ok = _kernel32.ReadProcessMemory(
            process,
            remote_text,
            text_buffer,
            buffer_size,
            ctypes.byref(bytes_read),
        )
        return text_buffer.value if ok else ""
    finally:
        _kernel32.VirtualFreeEx(process,remote_text,0,MEM_RELEASE)

def list_tray_toolbar_icons(toolbar_hwnd):
    _,pid = win32process.GetWindowThreadProcessId(toolbar_hwnd)
    access = PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | PROCESS_VM_READ
    process = _kernel32.OpenProcess(access,False,pid)
    if not process:
        return []

    remote_button = _kernel32.VirtualAllocEx(process,None,ctypes.sizeof(TBBUTTON),MEM_COMMIT,PAGE_READWRITE)
    if not remote_button:
        _kernel32.CloseHandle(process)
        return []

    items = []

    try:
        count = _user32.SendMessageW(toolbar_hwnd,TB_BUTTONCOUNT,0,0)
        for index in range(count):
            button = _read_tray_button(process,toolbar_hwnd,index,remote_button)
            if not button or not button.dwData:
                continue

            tray_data = _read_process_memory(process,button.dwData,TRAYDATA)
            if not tray_data or not tray_data.hicon:
                continue

            tooltip = _read_tray_tooltip(process,toolbar_hwnd,button)
            items.append({
                "id": f"{_raw_value(tray_data.hwnd)}:{tray_data.uid}:{tray_data.callback_message}",
                "tooltip": tooltip,
                "hwnd": _raw_value(tray_data.hwnd),
                "uid": int(tray_data.uid),
                "callback_message": int(tray_data.callback_message),
                "hicon": _raw_value(tray_data.hicon),
            })
    finally:
        _kernel32.VirtualFreeEx(process,remote_button,0,MEM_RELEASE)
        _kernel32.CloseHandle(process)

    return items

def list_tray_icons():
    items = []
    seen = set()

    for toolbar in get_tray_toolbars():
        for item in list_tray_toolbar_icons(toolbar):
            key = (item["hwnd"],item["uid"],item["callback_message"])
            if key in seen:
                continue
            seen.add(key)
            items.append(item)

    return items

def _make_lparam(low,high):
    return (low & 0xffff) | ((high & 0xffff) << 16)

def _tray_anchor_lparam(item):
    return _make_lparam(item.anchor_x,item.anchor_y)

def send_tray_icon_click(item,button="left"):
    hwnd = item.hwnd
    uid = item.uid
    callback_message = item.callback_message

    if not hwnd or uid is None or not callback_message:
        return False

    if button == "right":
        down = win32con.WM_RBUTTONDOWN
        up = win32con.WM_RBUTTONUP
        v4_up = win32con.WM_CONTEXTMENU
    else:
        down = win32con.WM_LBUTTONDOWN
        up = win32con.WM_LBUTTONUP
        v4_up = up

    try:
        if item.anchor_x or item.anchor_y:
            win32api.SetCursorPos((item.anchor_x,item.anchor_y))

        try:
            win32gui.SetForegroundWindow(hwnd)
        except win32gui.error:
            pass

        # Newer tray icons receive coordinates in wParam and the icon id in HIWORD(lParam).
        win32gui.PostMessage(hwnd,callback_message,_tray_anchor_lparam(item),_make_lparam(down,uid))
        win32gui.PostMessage(hwnd,callback_message,_tray_anchor_lparam(item),_make_lparam(v4_up,uid))

        # Older tray icons expect wParam=uid and lParam=mouse message.
        win32gui.PostMessage(hwnd,callback_message,uid,down)
        win32gui.PostMessage(hwnd,callback_message,uid,up)
        win32gui.PostMessage(hwnd,win32con.WM_NULL,0,0)
        return True
    except win32gui.error as e:
        print("couldn't send tray click:",e)
        return False

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

def get_window_process_name(hwnd):
    if not hwnd:
        return ""

    try:
        _,pid = win32process.GetWindowThreadProcessId(hwnd)
        return os.path.basename(psutil.Process(pid).name()).lower()
    except (psutil.NoSuchProcess,psutil.AccessDenied,psutil.ZombieProcess,win32gui.error):
        return ""

def get_foreground_window_title():
    hwnd = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(hwnd).strip() if hwnd else ""

def get_foreground_window_info():
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return {"hwnd": 0,"title": "","class_name": "","process": ""}

    return {
        "hwnd": hwnd,
        "title": win32gui.GetWindowText(hwnd).strip(),
        "class_name": win32gui.GetClassName(hwnd),
        "process": get_window_process_name(hwnd),
    }

def is_start_menu_open():
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return False

    process_name = get_window_process_name(hwnd)
    title = win32gui.GetWindowText(hwnd).strip().lower()

    return process_name in START_MENU_PROCESS_NAMES or title in START_MENU_TITLES
