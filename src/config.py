import json
from dataclasses import asdict,dataclass,field
from pathlib import Path
import sys

APP_VERSION = "0.6.9"

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
    taskbar_texture_opacity: float
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
    button_style: str
    padding_x: int
    padding_y: int
    gap: int
    tray_gap: int
    start_icon_transition: dict
    start_icon: str
    start_icon_size: int
    start_button_fx: bool
    start_button_width: int
    start_button_height: int
    start_button_hover: str
    start_button_active: str
    search_icon: str
    search_icon_size: int
    search_button_width: int
    search_button_height: int
    search_box_width: int
    search_box_height: int
    search_box_background: str
    search_box_foreground: str
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

#behavior config
@dataclass
class ClockBehaviorConfig:
    time_format: str = "hh:mm:ss"
    date_format: str = "dd/MM/yyyy"
    show_time: bool = True
    show_date: bool = False

@dataclass
class SearchBehaviorConfig:
    mode: str = "box"
    engine: str = "windows_search"
    box_clear_button: bool = False
    everything_path: str = r"C:\Program Files\Everything\Everything.exe"

@dataclass
class BehaviorConfig:
    clock: ClockBehaviorConfig = field(default_factory=ClockBehaviorConfig)
    search: SearchBehaviorConfig = field(default_factory=SearchBehaviorConfig)

@dataclass
class SettingsConfig:
    skin: str = "default"
    language: str = "en-US"

@dataclass
class SkinMetadata:
    id: str
    name: str
    author: str
    version: str

class Config:
    def __init__(self,config_dir="config"):
        global APP_VERSION

        self.root_dir = self._get_root_dir()
        self.config_dir = self._resolve_app_path(config_dir)
        self.base_assets_dir = self.root_dir/"assets"
        self.i18n_dir = self.root_dir/"i18n"
        self.skins_dir = self.config_dir/"skins"
        self.user_dir = self.config_dir/"user"

        #load user config
        with open(self.user_dir/"settings.json","r",encoding="utf-8") as f:
            settings_data = json.load(f)

        with open(self.user_dir/"apps.json","r",encoding="utf-8") as f:
            apps_data = json.load(f)

        with open(self.user_dir/"behavior.json","r",encoding="utf-8") as f:
            behavior_data = json.load(f)

        self.settings = SettingsConfig(**settings_data)
        self.apps = AppsConfig(**apps_data)
        self.behavior = BehaviorConfig(
            clock=ClockBehaviorConfig(**behavior_data.get("clock",{})),
            search=SearchBehaviorConfig(**behavior_data.get("search",{})),
        )

        #load skin config + metadata
        with open(self.skins_dir/self.settings.skin/"metadata.json","r",encoding="utf-8") as f:
            skin_md_data = json.load(f)

        with open(self.skins_dir/self.settings.skin/"layout.json","r",encoding="utf-8") as f:
            layout_data = json.load(f)

        with open(self.skins_dir/self.settings.skin/"theme.json","r",encoding="utf-8") as f:
            theme_data = json.load(f)

        self.skin_metadata = SkinMetadata(**skin_md_data)
        self.layout = LayoutConfig(**layout_data)
        self.theme = ThemeConfig(**theme_data)

        #get active skin
        self.active_skin_id = self.settings.skin
        self.active_skin_dir = self.skins_dir/self.settings.skin

        self.version = APP_VERSION

    def _get_root_dir(self) -> Path:
        if getattr(sys,"frozen",False) or Path(sys.argv[0]).suffix.lower() == ".exe":
            return Path(sys.argv[0]).resolve().parent

        return Path(__file__).resolve().parent.parent

    def _resolve_app_path(self,path: str | Path) -> Path:
        app_path = Path(path)
        if app_path.is_absolute():
            return app_path

        return self.root_dir/app_path

    def save_theme(self):
        with open(self.skins_dir/self.settings.skin/"theme.json","w",encoding="utf-8") as f:
            json.dump(asdict(self.theme),f,indent=4)
            f.write("\n")

    def save_layout(self):
        with open(self.skins_dir/self.settings.skin/"layout.json","w",encoding="utf-8") as f:
            json.dump(asdict(self.layout),f,indent=4)
            f.write("\n")

    def save_apps(self):
        with open(self.user_dir/"apps.json","w",encoding="utf-8") as f:
            json.dump(asdict(self.apps),f,indent=4)
            f.write("\n")

    def save_behavior(self):
        with open(self.user_dir/"behavior.json","w",encoding="utf-8") as f:
            json.dump(asdict(self.behavior),f,indent=4)
            f.write("\n")
    
    def save_settings(self):
        with open(self.user_dir/"settings.json","w",encoding="utf-8") as f:
            json.dump(asdict(self.settings),f,indent=4)
            f.write("\n")

    def save(self,section: str | None = None):
        if section == "theme":
            self.save_theme()
        elif section == "layout":
            self.save_layout()
        elif section == "apps":
            self.save_apps()
        elif section == "behavior":
            self.save_behavior()
        elif section == "settings":
            self.save_settings()
        else:
            self.save_theme()
            self.save_layout()
            self.save_apps()
            self.save_behavior()
            self.save_settings()

    def resolve_asset(self,relative_path: str | None) -> str | None:
        if not relative_path:
            return None

        rel = Path(relative_path)

        skin_candidate = self.active_skin_dir/rel
        if skin_candidate.exists():
            print(f"using skin asset: {relative_path}")
            return str(skin_candidate)

        base_candidate = self.base_assets_dir/rel.name
        if base_candidate.exists():
            print(f"using base asset: {relative_path}")
            return str(base_candidate)

        print(f"asset not found: {relative_path}")
        return str(skin_candidate)
    
    def resolve_skin_asset(self,filename: str | None) -> str | None:
        if not filename:
            return None
        return self.resolve_asset(f"assets/{filename}")

    def change_setting(self,section: str,*keys: str) -> bool:
        if not keys:
            return False

        target = getattr(self,section,None)
        if target is None:
            return False

        for key in keys[:-1]:
            target = getattr(target,key,None)
            if target is None:
                return False

        key = keys[-1]
        if not hasattr(target,key):
            return False

        current_value = getattr(target,key)

        if isinstance(current_value,bool):
            #toggle bool value
            setattr(target,key,not current_value)
            self.save(section)
            return True

        if isinstance(current_value,(str,int,float)):
            from PySide6.QtWidgets import QInputDialog

            value_text,accepted = QInputDialog.getText(
                None,"taskbarPlus",".".join((section,*keys)),
                text=str(current_value)
            )
            if not accepted:
                return False

            try:
                if isinstance(current_value,int):
                    new_value = int(value_text)
                elif isinstance(current_value,float):
                    new_value = float(value_text)
                else:
                    new_value = value_text
            except ValueError:
                return False

            setattr(target,key,new_value)
            self.save(section)
            return True

        return False