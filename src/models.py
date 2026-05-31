from __future__ import annotations
from PySide6.QtGui import QIcon,QPixmap
from dataclasses import dataclass,field

@dataclass
class WindowEntry:
    hwnd: int
    title: str
    path: str

@dataclass
class TaskbarItem:
    id: str
    title: str
    icon: QIcon
    hover_icon: QIcon | None = None
    active_icon: QIcon | None = None
    icon_pixmap: QPixmap | None = None
    hover_icon_pixmap: QPixmap | None = None
    active_icon_pixmap: QPixmap | None = None
    pinned: bool = False
    running: bool = False
    active: bool = False
    launch_path: str | None = None
    windows: list[WindowEntry] = field(default_factory=list)

@dataclass
class TrayItem:
    id: str
    icon: QIcon
    hover_icon: QIcon | None = None
    tooltip: str = ""
    hwnd: int | None = None
    uid: int | None = None
    callback_message: int | None = None
    anchor_x: int = 0
    anchor_y: int = 0
