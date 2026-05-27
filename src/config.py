import json
from dataclasses import dataclass
from pathlib import Path

@dataclass
class IconTheme:
    default: str
    hover: str | None = None

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
    background: str
    foreground: str
    hover: str
    active: str
    accent: str
    icon_size: int
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
    start_icon: IconTheme
    search_icon: IconTheme
    task_view_icon: IconTheme
    show_desktop_width: int
    show_desktop_border_color: str

@dataclass
class AppsConfig:
    pinned: list

class Config:
    def __init__(self,config_dir="config"):
        config_dir = Path(config_dir)

        with open(config_dir/"layout.json","r",encoding="utf-8") as f:
            layout_data = json.load(f)

        with open(config_dir/"theme.json","r",encoding="utf-8") as f:
            theme_data = json.load(f)

        for key in ("start_icon","search_icon","task_view_icon"):
            theme_data[key] = self.parse_icon_theme(theme_data[key])

        with open(config_dir/"apps.json","r",encoding="utf-8") as f:
            apps_data = json.load(f)

        self.layout = LayoutConfig(**layout_data)
        self.theme = ThemeConfig(**theme_data)
        self.apps = AppsConfig(**apps_data)

    def parse_icon_theme(self,value) -> IconTheme:
        if isinstance(value,str):
            return IconTheme(default=value)

        return IconTheme(
            default=value["default"],
            hover=value.get("hover")
        )