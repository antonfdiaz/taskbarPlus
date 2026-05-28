import ctypes
from PySide6.QtGui import QColor

ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19

class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState",ctypes.c_int),
        ("AccentFlags",ctypes.c_int),
        ("GradientColor",ctypes.c_uint32),
        ("AnimationId",ctypes.c_int),
    ]

class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute",ctypes.c_int),
        ("Data",ctypes.c_void_p),
        ("SizeOfData",ctypes.c_size_t),
    ]

def qt_color_to_abgr(color_str: str) -> int:
    color = QColor(color_str)
    a = color.alpha()
    r = color.red()
    g = color.green()
    b = color.blue()
    return (a << 24) | (b << 16) | (g << 8) | r

def apply_acrylic(hwnd: int,color: str = "#CC202020",acrylic: bool = True):
    accent = ACCENT_POLICY()
    accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND if acrylic else ACCENT_ENABLE_BLURBEHIND
    accent.AccentFlags = 2
    accent.GradientColor = qt_color_to_abgr(color)
    accent.AnimationId = 0

    data = WINDOWCOMPOSITIONATTRIBDATA()
    data.Attribute = WCA_ACCENT_POLICY
    data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
    data.SizeOfData = ctypes.sizeof(accent)

    ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))