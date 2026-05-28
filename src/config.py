import json
from dataclasses import dataclass
from pathlib import Path

@dataclass
class LayoutConfig:
    left: list
    center: list
    right: list

@dataclass
class ThemeConfig:
    taskbar_height: int
    taskbar_texture: str | None
    taskbar_texture_mode: str
    taskbar_blur: bool
    taskbar_blur_tint: str
    background: str
    foreground: str
    hover: str
    active: str
    accent: str
    icon_size: int
    icon_opacity: float
    tray_icon_size: int
    button_width: int
    button_height: int
    padding_x: int
    padding_y: int
    gap: int
    tray_gap: int
    menu_separator_color: str
    clock_format: str
    date_format: str
    start_icon_transition: dict
    start_icon: str
    start_icon_size: int
    search_icon: str
    search_icon_size: int
    task_view_icon: str
    task_view_icon_size: int
    show_desktop_width: int
    show_desktop_border_color: str

@dataclass
class AppsConfig:
    pinned: list

class Config:
    def __init__(self,config_dir="config"):
        self.config_dir = Path(config_dir)

        with open(self.config_dir/"layout.json","r",encoding="utf-8") as f:
            layout_data = json.load(f)

        with open(self.config_dir/"theme.json","r",encoding="utf-8") as f:
            theme_data = json.load(f)

        with open(self.config_dir/"apps.json","r",encoding="utf-8") as f:
            apps_data = json.load(f)

        self.layout = LayoutConfig(**layout_data)
        self.theme = ThemeConfig(**theme_data)
        self.apps = AppsConfig(**apps_data)

    def save_apps(self):
        with open(self.config_dir/"apps.json","w",encoding="utf-8") as f:
            json.dump({"pinned": self.apps.pinned},f,indent=4)
            f.write("\n")
