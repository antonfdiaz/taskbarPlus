import ctypes
from ctypes import wintypes
from PySide6.QtCore import QObject,Signal

EVENT_SYSTEM_FOREGROUND = 0x0003
EVENT_OBJECT_CREATE = 0x8000
EVENT_OBJECT_DESTROY = 0x8001
EVENT_OBJECT_SHOW = 0x8002
EVENT_OBJECT_HIDE = 0x8003
OBJID_WINDOW = 0
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002

WinEventProc = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD
)

user32 = ctypes.windll.user32
user32.SetWinEventHook.argtypes = [
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HMODULE,
    WinEventProc,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD
]
user32.SetWinEventHook.restype = wintypes.HANDLE
user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
user32.UnhookWinEvent.restype = wintypes.BOOL

class WindowEventWatcher(QObject):
    foregroundChanged = Signal(object)
    windowsChanged = Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.hooks = []
        self.callback = WinEventProc(self.on_event)

        self.add_hook(EVENT_SYSTEM_FOREGROUND,EVENT_SYSTEM_FOREGROUND)
        self.add_hook(EVENT_OBJECT_CREATE,EVENT_OBJECT_HIDE)

    def add_hook(self,event_min: int,event_max: int):
        hook = user32.SetWinEventHook(
            event_min,event_max,0,self.callback,
            0,0,WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS
        )
        if hook:
            self.hooks.append(hook)

    def on_event(self,hook,event,hwnd,id_object,id_child,event_thread,event_time):
        if id_object != OBJID_WINDOW:
            return

        if event == EVENT_SYSTEM_FOREGROUND:
            self.foregroundChanged.emit(int(hwnd))
        elif event in (EVENT_OBJECT_CREATE,EVENT_OBJECT_DESTROY,EVENT_OBJECT_SHOW,EVENT_OBJECT_HIDE):
            self.windowsChanged.emit()

    def stop(self):
        for hook in self.hooks:
            user32.UnhookWinEvent(hook)
        self.hooks = []

    def __del__(self):
        self.stop()