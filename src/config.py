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
    background: str
    foreground: str
    hover: str
    active: str
    accent: str
    icon_size: int
    button_width: int
    button_height: int
    padding_x: int
    padding_y: int
    gap: int

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

        with open(config_dir/"apps.json","r",encoding="utf-8") as f:
            apps_data = json.load(f)

        self.layout = LayoutConfig(**layout_data)
        self.theme = ThemeConfig(**theme_data)
        self.apps = AppsConfig(**apps_data)