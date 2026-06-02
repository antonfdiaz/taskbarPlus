import json
from dataclasses import asdict, dataclass
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
    clock_time_format: str
    clock_date_format: str
    clock_time_visible: bool
    clock_date_visible: bool
    start_icon_transition: dict
    start_icon: str
    start_icon_size: int
    start_button_width: int
    start_button_height: int
    start_button_hover: str
    start_button_active: str
    search_mode: str
    search_engine: str
    search_icon: str
    search_icon_size: int
    search_button_width: int
    search_button_height: int
    search_box_width: int
    search_box_height: int
    search_box_background: str
    search_box_foreground: str
    search_box_clear_button: bool
    everything_path: str
    task_view_icon: str
    task_view_icon_size: int
    task_view_button_width: int
    task_view_button_height: int
    show_desktop_width: int
    show_desktop_border_color: str
    menu_background: str
    menu_foreground: str
    menu_hover: str
    menu_separator_color: str

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

    def save_theme(self):
        with open(self.config_dir/"theme.json","w",encoding="utf-8") as f:
            json.dump(asdict(self.theme),f,indent=4)
            f.write("\n")

    def save_layout(self):
        with open(self.config_dir/"layout.json","w",encoding="utf-8") as f:
            json.dump(asdict(self.layout),f,indent=4)
            f.write("\n")

    def save_apps(self):
        with open(self.config_dir/"apps.json","w",encoding="utf-8") as f:
            json.dump(asdict(self.apps),f,indent=4)
            f.write("\n")

    def save(self, section: str | None = None):
        if section == "theme":
            self.save_theme()
        elif section == "layout":
            self.save_layout()
        elif section == "apps":
            self.save_apps()
        else:
            self.save_theme()
            self.save_layout()
            self.save_apps()
