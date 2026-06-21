from __future__ import annotations
from collections import defaultdict
import json
from pathlib import Path
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import QTimer,Qt,Signal
from src.l18n import L18n
from src.config import Config,SkinMetadata
from src.models import *
from src.widgets import *
from src.shell import *
from src.blur import apply_acrylic
from src.utils import theme_color_css,menu_style,theme_color
from src.win_observer import WindowEventWatcher
import subprocess
import win32gui
import win32con
import os

class TaskbarRootWidget(QWidget):
    """Root widget of the taskbar. Paints the background and texture."""
    def __init__(self,config: Config,parent=None):
        super().__init__(parent)
        self.config = config
        self.texture = QPixmap()

        texture_path = self.config.resolve_asset(self.config.theme.taskbar_texture)
        if texture_path:
            self.texture = QPixmap(texture_path)

    def paintEvent(self,event):
        painter = QPainter(self)

        try:
            background = theme_color(self.config.theme.background)
            if background.alpha() == 0:
                background.setAlpha(1)
            painter.fillRect(self.rect(),background)

            if self.texture.isNull():
                return

            opacity = max(0.0,min(1.0,float(self.config.theme.taskbar_texture_opacity)))
            if opacity <= 0.0:
                return

            painter.save()
            painter.setOpacity(opacity)

            if self.config.theme.taskbar_texture_mode == "tile":
                painter.drawTiledPixmap(self.rect(),self.texture)
            else:
                painter.drawPixmap(
                    self.rect(),
                    self.texture.scaled(
                        self.size(),
                        Qt.IgnoreAspectRatio,
                        Qt.SmoothTransformation
                    )
                )

            painter.restore()
        finally:
            painter.end()

class MainWindow(QMainWindow):
    """Main taskbar window. Does a lot of stuff."""

    config_reload_requested = Signal()

    def __init__(self,config: Config):
        super().__init__()
        self.config: Config = config
        self.load_l18n()
        self.app_order: list[str] = []
        self.apps_bars: list[TaskbarAppsBar] = []
        self.start_buttons: list[TaskbarButton] = []
        self.tray_widgets: list[TrayWidget] = []
        self.tray_collapsed = False
        self.tray_items: list[TrayItem] = []
        self.apps_refresh_pending = False
        self.start_menu_open = False
        self.config_reload_requested.connect(self.reload_from_disk)

        self.setup_window()
        self.rebuild_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_apps)
        self.timer.start(5000)

        self.start_menu_timer = QTimer(self)
        self.start_menu_timer.timeout.connect(self.refresh_start_button_state)
        self.start_menu_timer.start(100)

        self.window_events = WindowEventWatcher(self)
        self.window_events.foregroundChanged.connect(self.refresh_active_window)
        self.window_events.windowsChanged.connect(self.schedule_apps_refresh)

    def tr(self,key: str) -> str:
        return self.l18n.tr(key)

    def load_l18n(self):
        try:
            self.l18n = L18n(self.config.i18n_dir/f"{self.config.settings.language}.json")
        except Exception as e:
            print("couldn't load language file, falling back to default:",e)
            msgbox = QMessageBox(self)
            msgbox.setIcon(QMessageBox.Warning)
            msgbox.setWindowTitle("taskbarPlus")
            msgbox.setText("Couldn't load language file, falling back to default.")
            msgbox.setInformativeText(f"Error details:\n{e}")
            msgbox.exec()
            self.l18n = L18n(self.config.i18n_dir/"en-US.json")

    def setup_window(self):
        screen_size = QGuiApplication.primaryScreen().size()

        self.setStyleSheet("background: transparent;")
        self.setWindowTitle("taskbarPlus")
        self.setGeometry(0,screen_size.height()-self.config.theme.taskbar_height,screen_size.width(),self.config.theme.taskbar_height)
        self.setFixedSize(screen_size.width(),self.config.theme.taskbar_height)
        self.setAttribute(Qt.WA_TranslucentBackground,True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAcceptDrops(True)

        if self.config.theme.taskbar_blur:
            try:
                apply_acrylic(int(self.winId()),color=self.config.theme.taskbar_blur_tint,acrylic=True)
            except Exception as e:
                print("couldn't apply acrylic blur:",e)

        self.menu = QMenu(self)
        self.rebuild_context_menu()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda pos: self.menu.exec(self.mapToGlobal(pos)))

    def rebuild_context_menu(self):
        self.menu.clear()
        self.menu.setStyleSheet(menu_style(self.config))
        self.menu.addAction(self.tr("taskbar.menu.task_manager"),lambda: launch_windows_app("taskmgr.exe")).setIcon(QIcon(self.config.resolve_asset("assets/taskmgr.png")).pixmap(16,16))
        self.menu.addSeparator()
        self.skins_menu = self.create_skins_menu()
        self.menu.addMenu(self.skins_menu)
        self.lang_menu = self.create_lang_menu()
        self.menu.addMenu(self.lang_menu)
        self.behavior_menu = self.create_behavior_menu()
        self.menu.addMenu(self.behavior_menu)
        self.menu.addAction(self.tr("taskbar.menu.about"),self.show_about_dialog).setIcon(QIcon(self.config.resolve_asset("assets/info.png")).pixmap(16,16))
        self.menu.addAction(self.tr("taskbar.menu.refresh"),self.rebuild_ui).setIcon(QIcon(self.config.resolve_asset("assets/refresh.png")).pixmap(16,16))
        self.menu.addAction(self.tr("taskbar.menu.exit"),self.close).setIcon(QIcon(self.config.resolve_asset("assets/close.png")).pixmap(16,16))

    def show_about_dialog(self):
        msg = QMessageBox(self)
        msg.setStyleSheet(f"background-color: {self.config.theme.menu_background}; color: {self.config.theme.menu_foreground};")
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(self.tr("taskbar.about.title"))
        msg.setText(f"taskbarPlus {self.config.version}")
        msg.setInformativeText(self.tr("taskbar.about.description"))
        msg.exec()

    def create_behavior_menu(self) -> QMenu:
        self.behavior_menu = QMenu(self.tr("taskbar.menu.behavior"),self)
        self.behavior_menu.setStyleSheet(menu_style(self.config))
        self.behavior_menu.setIcon(QIcon(self.config.resolve_asset("assets/setting.png")).pixmap(16,16))

        self.clock_behavior_menu = QMenu(self.tr("taskbar.menu.behavior.clock"),self.behavior_menu)
        self.clock_behavior_menu.setStyleSheet(menu_style(self.config))
        self.clock_behavior_menu.setToolTipsVisible(True)

        time_format_action = self.clock_behavior_menu.addAction(
            self.tr("taskbar.menu.behavior.clock.time_format"),
            lambda: self.change_setting("behavior","clock","time_format")
        )
        time_format_action.setToolTip(self.config.behavior.clock.time_format)

        date_format_action = self.clock_behavior_menu.addAction(
            self.tr("taskbar.menu.behavior.clock.date_format"),
            lambda: self.change_setting("behavior","clock","date_format")
        )
        date_format_action.setToolTip(self.config.behavior.clock.date_format)

        show_time_action = self.clock_behavior_menu.addAction(
            self.tr("taskbar.menu.behavior.clock.show_time"),
            lambda: self.change_setting("behavior","clock","show_time")
        )
        show_time_action.setCheckable(True)
        show_time_action.setChecked(self.config.behavior.clock.show_time)

        show_date_action = self.clock_behavior_menu.addAction(
            self.tr("taskbar.menu.behavior.clock.show_date"),
            lambda: self.change_setting("behavior","clock","show_date")
        )
        show_date_action.setCheckable(True)
        show_date_action.setChecked(self.config.behavior.clock.show_date)

        font_size_action = self.clock_behavior_menu.addAction(
            self.tr("taskbar.menu.behavior.clock.font_size"),
            lambda: self.change_setting("behavior","clock","font_size")
        )
        font_size_action.setToolTip(self.config.behavior.clock.font_size)

        self.behavior_menu.addMenu(self.clock_behavior_menu)

        self.search_behavior_menu = QMenu(self.tr("taskbar.menu.behavior.search"),self.behavior_menu)
        self.search_behavior_menu.setStyleSheet(menu_style(self.config))
        self.search_behavior_menu.setToolTipsVisible(True)

        search_mode_action = self.search_behavior_menu.addAction(
            self.tr("taskbar.menu.behavior.search.mode"),
            lambda: self.change_setting("behavior","search","mode")
        )
        search_mode_action.setToolTip(self.config.behavior.search.mode)

        search_engine_action = self.search_behavior_menu.addAction(
            self.tr("taskbar.menu.behavior.search.engine"),
            lambda: self.change_setting("behavior","search","engine")
        )
        search_engine_action.setToolTip(self.config.behavior.search.engine)

        box_clear_button_action = self.search_behavior_menu.addAction(
            self.tr("taskbar.menu.behavior.search.box_clear_button"),
            lambda: self.change_setting("behavior","search","box_clear_button")
        )
        box_clear_button_action.setCheckable(True)
        box_clear_button_action.setChecked(self.config.behavior.search.box_clear_button)

        everything_path_action = self.search_behavior_menu.addAction(
            self.tr("taskbar.menu.behavior.search.everything_path"),
            lambda: self.change_setting("behavior","search","everything_path")
        )
        everything_path_action.setToolTip(self.config.behavior.search.everything_path)

        self.behavior_menu.addMenu(self.search_behavior_menu)

        self.taskbar_behavior_menu = QMenu(self.tr("taskbar.menu.behavior.taskbar"),self.behavior_menu)
        self.taskbar_behavior_menu.setStyleSheet(menu_style(self.config))

        combine_taskbar_btns_action = self.taskbar_behavior_menu.addAction(
            self.tr("taskbar.menu.behavior.taskbar.combine_taskbar_btns"),
            lambda: self.change_setting("behavior","taskbar","combine_taskbar_btns")
        )
        combine_taskbar_btns_action.setCheckable(True)
        combine_taskbar_btns_action.setChecked(self.config.behavior.taskbar.combine_taskbar_btns)

        self.behavior_menu.addMenu(self.taskbar_behavior_menu)

        return self.behavior_menu

    def change_setting(self,section: str,*keys: str):
        if self.config.change_setting(section,*keys):
            QTimer.singleShot(100,self.reload_from_disk)

    def create_lang_menu(self) -> QMenu:
        self.locale_lang = {
            "en-US": "English",
            "en-GB": "English (UK)",
            "es-ES": "Spanish",
            "es-MX": "Spanish (Mexico)",
            "es-419": "Spanish (Latin America)",
            "gl-ES": "Galician",
            "ca-ES": "Catalan",
            "eu-ES": "Basque",
            "fr-FR": "French",
            "de-DE": "German",
            "it-IT": "Italian",
            "pt-PT": "Portuguese",
            "pt-BR": "Portuguese (Brazil)",
            "nl-NL": "Dutch",
            "pl-PL": "Polish",
            "ru-RU": "Russian",
            "uk-UA": "Ukrainian",
            "zh-CN": "Chinese (Simplified)",
            "zh-TW": "Chinese (Traditional)",
            "ja-JP": "Japanese",
            "ko-KR": "Korean",
            "ar-SA": "Arabic",
            "tr-TR": "Turkish",
            "hi-IN": "Hindi",
            "id-ID": "Indonesian",
            "vi-VN": "Vietnamese",
        }

        lang_menu = QMenu(self.tr("taskbar.menu.language"),self)
        lang_menu.setStyleSheet(menu_style(self.config))
        lang_menu.setToolTipsVisible(True)
        lang_menu.setIcon(QIcon(self.config.resolve_asset("assets/language.png")).pixmap(16,16))

        languages_dir = self.config.i18n_dir
        if not languages_dir.exists():
            return lang_menu

        for lang_file in languages_dir.iterdir():
            if not lang_file.is_file() or lang_file.suffix.lower() != ".json":
                continue

            lang_code = lang_file.stem
            lang_name = self.locale_lang.get(lang_code,lang_code)
            action = lang_menu.addAction(lang_name)
            action.setCheckable(True)
            action.setChecked(lang_code == self.config.settings.language)
            action.triggered.connect(lambda checked=False,code=lang_code: self.change_lang(code))

        return lang_menu
    
    def change_lang(self,lang_code: str):
        if lang_code == self.config.settings.language:
            return

        for action in self.lang_menu.actions():
            action.setChecked(action.text() == self.locale_lang.get(lang_code,lang_code))

        self.config.settings.language = lang_code
        self.config.save_settings()
        self.reload_from_disk()

    def create_skins_menu(self) -> QMenu:
        skins_menu = QMenu(self.tr("taskbar.menu.skins"),self)
        skins_menu.setStyleSheet(menu_style(self.config))
        skins_menu.setToolTipsVisible(True)
        skins_menu.setIcon(QIcon(self.config.resolve_asset("assets/skin.png")).pixmap(16,16))

        skins_dir = self.config.config_dir/"skins"
        if not skins_dir.exists():
            return skins_menu

        for skin_dir in skins_dir.iterdir():
            if not skin_dir.is_dir():
                continue

            metadata_path = skin_dir/"metadata.json"
            if not metadata_path.exists():
                continue
            else:
                try:
                    metadata = SkinMetadata(**json.loads(metadata_path.read_text(encoding="utf-8")))
                except Exception as e:
                    print(f"couldn't load skin metadata from {metadata_path}:",e)
                    continue

            action = skins_menu.addAction(metadata.name)
            action.setToolTip(self.tr("taskbar.skin.tooltip").format(metadata=metadata))
            action.setCheckable(True)
            action.setChecked(skin_dir.name == self.config.settings.skin)
            action.triggered.connect(lambda checked=False,skin=skin_dir.name: self.change_skin(skin))

        return skins_menu
    
    def change_skin(self,skin_name: str):
        if skin_name == self.config.settings.skin:
            return

        for action in self.skins_menu.actions():
            action.setChecked(action.text() == skin_name)

        self.config.settings.skin = skin_name
        self.config.save_settings()
        self.reload_from_disk()

    def rebuild_ui(self):
        self.load_l18n()
        self.apps_bars = []
        self.start_buttons = []
        self.tray_widgets = []
        self.tray_items = []

        screen_size = QGuiApplication.primaryScreen().size()
        self.setGeometry(0,screen_size.height()-self.config.theme.taskbar_height,screen_size.width(),self.config.theme.taskbar_height)
        self.setFixedSize(screen_size.width(),self.config.theme.taskbar_height)

        if self.config.theme.taskbar_blur:
            try:
                apply_acrylic(int(self.winId()),color=self.config.theme.taskbar_blur_tint,acrylic=True)
            except Exception as e:
                print("couldn't apply acrylic blur:",e)

        self.rebuild_context_menu()

        central_widget = TaskbarRootWidget(self.config)
        central_widget.setObjectName("taskbarRoot")
        self.setCentralWidget(central_widget)

        central_widget.setStyleSheet(f"""
            QWidget#taskbarRoot {{
                color: {theme_color_css(self.config.theme.foreground)};
            }}
        """)

        layout = QGridLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        central_widget.setLayout(layout)

        sections = [*self.config.layout.left,*self.config.layout.center,*self.config.layout.right]
        apps_items = self.build_taskbar_items() if "apps" in sections else []

        left_container = self.build_section(self.config.layout.left,apps_items)
        center_container = self.build_section(self.config.layout.center,apps_items)
        right_container = self.build_section(self.config.layout.right,apps_items)

        edge_container = QWidget()
        edge_layout = QHBoxLayout()
        edge_layout.setContentsMargins(0,0,0,0)
        edge_layout.setSpacing(0)
        edge_container.setLayout(edge_layout)

        edge_layout.addWidget(left_container)
        edge_layout.addStretch()
        edge_layout.addWidget(right_container)

        layout.addWidget(edge_container,0,0)
        layout.addWidget(center_container,0,0,alignment=Qt.AlignCenter)

    def reload_from_disk(self):
        if QApplication.activePopupWidget() is not None:
            return

        self.config = Config()
        self.rebuild_ui()

    def on_start_clicked(self):
        tap_key(win32con.VK_LWIN)
        QTimer.singleShot(80,self.refresh_start_button_state)
    
    def on_search_clicked(self):
        if self.config.behavior.search.engine == "everything":
            thread = Thread(target=lambda: subprocess.run(f'"{self.config.behavior.search.everything_path}"',shell=True))
            thread.start()
        elif self.config.behavior.search.engine == "windows_search":
            press_key(win32con.VK_LWIN)
            tap_key(ord("S"))
            release_key(win32con.VK_LWIN)

    def on_task_view_clicked(self):
        press_key(win32con.VK_LWIN)
        tap_key(win32con.VK_TAB)
        release_key(win32con.VK_LWIN)

    def build_section(self,sections: list[str],apps_items: list[TaskbarItem]) -> QWidget:
        container = QWidget()
        section_layout = QHBoxLayout()
        section_layout.setContentsMargins(0,0,0,0)
        section_layout.setSpacing(self.config.theme.gap)
        container.setLayout(section_layout)

        for section in sections:
            if section == "start":
                widget = self.create_button("start",self.tr("taskbar.button.start"),self.config.resolve_asset(self.config.theme.start_icon),self.on_start_clicked)
            elif section == "search":
                if self.config.behavior.search.mode == "box":
                    widget = SearchBox(self.config,self.l18n)
                elif self.config.behavior.search.mode == "icon":
                    widget = self.create_button("search",self.tr("taskbar.button.search"),self.config.resolve_asset(self.config.theme.search_icon),self.on_search_clicked)
            elif section == "task_view":
                widget = self.create_button("task_view",self.tr("taskbar.button.task_view"),self.config.resolve_asset(self.config.theme.task_view_icon),self.on_task_view_clicked)
            elif section == "apps":
                widget = TaskbarAppsBar(apps_items,self.config,self.l18n)
                widget.itemClicked.connect(self.on_item_clicked)
                widget.appDropped.connect(self.pin_app_from_path)
                widget.appReordered.connect(self.reorder_apps)
                self.apps_bars.append(widget)
            elif section == "tray":
                collapse_button = TrayCollapseButton(self.config)
                tray_items = self.build_tray_items()
                widget = TrayWidget(tray_items,self.config)
                widget.set_collapsed(self.tray_collapsed)
                collapse_button.set_collapsed(self.tray_collapsed)
                collapse_button.clicked.connect(
                    lambda checked=False,tray_widget=widget,button=collapse_button: self.toggle_tray_widget(tray_widget,button)
                )
                widget.itemClicked.connect(self.on_tray_item_clicked)
                widget.itemRightClicked.connect(self.on_tray_item_right_clicked)
                self.tray_widgets.append(widget)
                section_layout.addWidget(collapse_button)
            elif section == "clock":
                widget = ClockWidget(self.config,show_date=self.config.behavior.clock.show_date,show_time=self.config.behavior.clock.show_time)
            elif section == "show_desktop":
                widget = ShowDesktopButton(self.config)
            else:
                continue

            section_layout.addWidget(widget)

        return container

    def toggle_tray_widget(self,tray_widget: TrayWidget,collapse_button: TrayCollapseButton):
        tray_widget.toggle_collapsed()
        self.tray_collapsed = tray_widget.collapsed
        collapse_button.set_collapsed(tray_widget.collapsed)
    
    def build_tray_items(self) -> list[TrayIcon]:
        items = []
        tray_icons = list_tray_icons()

        if tray_icons:
            self.tray_items = [
                self.create_tray_item(item)
                for item in tray_icons
            ]

        for item in self.tray_items:
            items.append(TrayIcon(item,self.config))

        return items

    def create_tray_item(self,item) -> TrayItem:
        image = QImage.fromHICON(item["hicon"])
        icon = QIcon(QPixmap.fromImage(image)) if not image.isNull() else QIcon()

        return TrayItem(
            id=item["id"],
            icon=icon,
            tooltip=item["tooltip"],
            hwnd=item["hwnd"],
            uid=item["uid"],
            callback_message=item["callback_message"]
        )

    def on_tray_item_clicked(self,item: TrayItem):
        tooltip = item.tooltip.lower()
        if any(word in tooltip for word in ("network","internet","wi-fi","wifi","red")):
            subprocess.Popen(["explorer.exe","ms-availablenetworks:"])
            return

        if any(word in tooltip for word in ("volume","volumen","speaker","audio","sonido")):
            launch_windows_app("sndvol.exe")
            return

        send_tray_icon_click(item,"left")

    def on_tray_item_right_clicked(self,item: TrayItem):
        send_tray_icon_click(item,"right")

    def create_button(self,item_id: str,title: str,icon_path: str,handler) -> TaskbarButton:
        pixmaps = self.load_button_pixmaps(icon_path,item_id)
        icons = [QIcon(pixmap) for pixmap in pixmaps] if pixmaps else [QIcon(icon_path)]
        button = TaskbarButton(
            TaskbarItem(
                id=item_id,
                title=title,
                icon=icons[0],
                hover_icon=icons[1] if len(icons) >= 2 else None,
                active_icon=icons[2] if len(icons) >= 3 else None,
                icon_pixmap=pixmaps[0] if len(pixmaps) >= 1 else None,
                hover_icon_pixmap=pixmaps[1] if len(pixmaps) >= 2 else None,
                active_icon_pixmap=pixmaps[2] if len(pixmaps) >= 3 else None
            ),
            self.config,
            self.l18n
        )
        button.setToolTip(title)
        button.clicked.connect(handler)
        if item_id == "start":
            self.start_buttons.append(button)
            button.item.active = self.start_menu_open
        return button

    def load_button_pixmaps(self,path: str,item_id: str) -> list[QPixmap]:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return []

        width = pixmap.width()
        height = pixmap.height()

        if item_id == "start":
            animated_frames = self.load_animated_start_button_frames(pixmap)
            if animated_frames:
                return animated_frames

        if height > width and height % width == 0:
            frame_size = width
            frame_count = min(height // width,3)
            return [
                pixmap.copy(0,frame_size * index,frame_size,frame_size)
                for index in range(frame_count)
            ]

        if width > height and width % height == 0:
            frame_size = height
            frame_count = min(width // height,3)
            return [
                pixmap.copy(frame_size * index,0,frame_size,frame_size)
                for index in range(frame_count)
            ]

        if item_id == "start" and width != height:
            start_frames = self.load_start_button_frames(pixmap)
            if start_frames:
                return start_frames

        return [pixmap]

    def load_start_button_frames(self,pixmap: QPixmap) -> list[QPixmap]:
        width = pixmap.width()
        height = pixmap.height()
        candidates = []

        if height % 3 == 0:
            frame_height = height // 3
            if frame_height > 0:
                candidates.append((
                    abs((width / frame_height) - (self.config.theme.start_button_width / self.config.theme.start_button_height)),
                    [
                        pixmap.copy(0,frame_height * index,width,frame_height)
                        for index in range(3)
                    ]
                ))

        if width % 3 == 0:
            frame_width = width // 3
            if frame_width > 0:
                candidates.append((
                    abs((frame_width / height) - (self.config.theme.start_button_width / self.config.theme.start_button_height)),
                    [
                        pixmap.copy(frame_width * index,0,frame_width,height)
                        for index in range(3)
                    ]
                ))

        if not candidates:
            return []

        candidates.sort(key=lambda candidate: candidate[0])
        return candidates[0][1]

    def load_animated_start_button_frames(self,pixmap: QPixmap) -> list[QPixmap]:
        image = pixmap.toImage()
        if image.width() < 6 or image.height() < 2:
            return []

        if (
            image.pixelColor(0,0).getRgb()[:3] != (65,78,77) or
            image.pixelColor(1,0).getRgb()[:3] != (66,84,78)
        ):
            return []

        frame_info = image.pixelColor(2,0)
        description_rows = frame_info.red()
        frame_count = frame_info.blue()
        if description_rows <= 0 or frame_count <= 0:
            return []

        frames_height = image.height() - description_rows
        if frames_height <= 0 or frames_height % frame_count != 0:
            return []

        frame_height = frames_height // frame_count
        if frame_height <= 0:
            return []

        state_indexes = [
            image.pixelColor(index,0).blue()
            for index in range(3,6)
        ]
        if any(index >= frame_count for index in state_indexes):
            return []

        return [
            pixmap.copy(0,description_rows + frame_height * index,image.width(),frame_height)
            for index in state_indexes
        ]

    def normalize_path(self,path: str | None) -> str | None:
        if not path:
            return None
        return os.path.normcase(os.path.normpath(path))

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self,event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and self.pin_app_from_path(path):
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def resolve_shortcut_path(self,path: Path) -> Path:
        if path.suffix.lower() != ".lnk":
            return path

        try:
            import win32com.client

            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(str(path))
            if shortcut.TargetPath:
                return Path(shortcut.TargetPath)
        except Exception as e:
            print("couldn't resolve shortcut with win32com:",e)

        return path

    def pin_app_from_path(self,path: str) -> bool:
        dropped_path = Path(path)
        file_path = self.resolve_shortcut_path(dropped_path)
        if not file_path.exists() or not file_path.is_file():
            return False

        normalized_path = self.normalize_path(str(file_path))
        for app in self.config.apps.pinned:
            if self.normalize_path(app.get("path")) == normalized_path:
                return False

        app_id = file_path.stem.lower().replace(" ","_")
        existing_ids = {app.get("id") for app in self.config.apps.pinned}
        unique_id = app_id
        counter = 2
        while unique_id in existing_ids:
            unique_id = f"{app_id}_{counter}"
            counter += 1

        self.config.apps.pinned.append({
            "id": unique_id,
            "title": dropped_path.stem,
            "path": str(file_path).replace("\\","/")
        })
        self.config.save_apps()
        self.refresh_apps()
        return True

    def toggle_pinned_app(self,item: TaskbarItem):
        if not item.launch_path:
            return

        normalized_path = self.normalize_path(item.launch_path)
        if item.pinned:
            self.config.apps.pinned = [
                app for app in self.config.apps.pinned
                if self.normalize_path(app.get("path")) != normalized_path
            ]
            self.config.save_apps()
            self.refresh_apps()
            return

        self.pin_app_from_path(item.launch_path)

    def build_taskbar_items(self) -> list[TaskbarItem]:
        items = []
        open_windows = list_open_windows()
        grouped = defaultdict(list)
        active_hwnd = win32gui.GetForegroundWindow()

        #group open windows by their path
        for w in open_windows:
            path = w["path"]
            if not path:
                continue

            normalized_path = self.normalize_path(path)
            grouped[normalized_path].append(WindowEntry(
                hwnd=w["hwnd"],
                title=w["title"],
                path=path
            ))

        used_paths = set()

        for app in self.config.apps.pinned:
            path = app.get("path")
            normalized_path = self.normalize_path(path)
            windows = grouped.get(normalized_path,[]) if normalized_path else []
            is_active = any(w.hwnd == active_hwnd for w in windows)

            icon = get_app_icon(path,self.config.theme.icon_size) if path else QIcon()

            items.append(TaskbarItem(
                id=app["id"],
                title=app["title"],
                icon=icon,
                pinned=True,
                running=len(windows) > 0,
                active=is_active,
                launch_path=path,
                windows=windows
            ))

            if normalized_path:
                used_paths.add(normalized_path)

        dynamic_items: dict[str, TaskbarItem] = {}

        for normalized_path,windows in grouped.items():
            if normalized_path in used_paths:
                continue

            first = windows[0]
            is_active = any(w.hwnd == active_hwnd for w in windows)

            dynamic_items[normalized_path] = TaskbarItem(
                id=normalized_path,
                title=first.title,
                icon=get_app_icon(first.path,self.config.theme.icon_size),
                pinned=False,
                running=True,
                active=is_active,
                launch_path=first.path,
                windows=windows
            )

        all_items = {item.id: item for item in items}
        all_items.update(dynamic_items)
        stable_order = [item_id for item_id in self.app_order if item_id in all_items]
        for item_id in all_items:
            if item_id not in stable_order:
                stable_order.append(item_id)
        self.app_order = stable_order
        items = [all_items[item_id] for item_id in stable_order]

        return items

    def reorder_apps(self,from_index: int,to_index: int):
        if not self.apps_bars:
            return

        items = list(self.apps_bars[0].items)
        if not (0 <= from_index < len(items) and 0 <= to_index < len(items)):
            return

        item = items.pop(from_index)
        items.insert(to_index,item)
        self.app_order = [item.id for item in items]

        pinned_ids = set(self.app_order)
        self.config.apps.pinned.sort(
            key=lambda app: self.app_order.index(app["id"]) if app.get("id") in pinned_ids else len(self.app_order)
        )
        self.config.save_apps()

        QTimer.singleShot(0,lambda items=items: self.set_apps_bar_items(items))

    def set_apps_bar_items(self,items: list[TaskbarItem]):
        for apps_bar in self.apps_bars:
            apps_bar.set_items(items)
    
    def refresh_apps(self):
        self.apps_refresh_pending = False

        if not self.apps_bars and not self.tray_widgets:
            return

        if QApplication.activePopupWidget() is not None:
            return

        if self.apps_bars:
            items = self.build_taskbar_items()
            for apps_bar in self.apps_bars:
                apps_bar.set_items(items)

        if self.tray_widgets:
            for tray_widget in self.tray_widgets:
                tray_widget.set_items(self.build_tray_items())

    def schedule_apps_refresh(self,delay=120):
        if self.apps_refresh_pending:
            return

        self.apps_refresh_pending = True
        QTimer.singleShot(delay,self.refresh_apps)

    def refresh_active_window(self,hwnd: int | None = None):
        if hwnd is None:
            hwnd = win32gui.GetForegroundWindow()

        for apps_bar in self.apps_bars:
            apps_bar.set_active_window(hwnd)

        self.refresh_start_button_state()

    def refresh_start_button_state(self):
        if not self.start_buttons:
            self.start_menu_open = False
            return

        menu_open = is_start_menu_open()
        if menu_open == self.start_menu_open:
            return

        self.start_menu_open = menu_open
        for button in self.start_buttons:
            button.item.active = menu_open
            button.update()

    def on_item_clicked(self,item: TaskbarItem,button: object):
        if button == "pin":
            self.toggle_pinned_app(item)
            return

        if isinstance(button,int):
            activate_window(button,self)
            return

        count = len(item.windows)

        if count == 0:
            if item.launch_path:
                launch_windows_app(item.launch_path)
                self.schedule_apps_refresh()
        elif count == 1:
            hwnd = item.windows[0].hwnd
            activate_window(hwnd,self)
        else:
            self.show_windows_menu(item,button)

    def show_windows_menu(self,item: TaskbarItem,button: QWidget):
        menu = QMenu(self)
        menu.setStyleSheet(menu_style(self.config))

        for window in item.windows:
            action = menu.addAction(window.title)
            action.triggered.connect(
                lambda checked=False,hwnd=window.hwnd: activate_window(hwnd,self)
            )

        new_win_action = menu.addAction(self.tr("taskbar.menu.new_win"))
        new_win_action.setIcon(QIcon(self.config.resolve_asset("assets/add.png")).pixmap(15,15))
        new_win_action.triggered.connect(
            lambda checked=False,path=item.launch_path: launch_windows_app(path) if path else None
        )

        pos = button.mapToGlobal(button.rect().topLeft())
        pos.setY(pos.y()-menu.sizeHint().height())
        menu.exec(pos)
