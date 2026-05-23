from PySide6.QtGui import QIcon
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
    pinned: bool = False
    running: bool = False
    active: bool = False
    launch_path: str | None = None
    windows: list[WindowEntry] = field(default_factory=list)