from collections import defaultdict
import os
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import QTimer
from src.config import Config
from src.models import *
from src.widgets import *
from src.shell import *
import subprocess
import win32gui
import win32con

class MainWindow(QMainWindow):
    def __init__(self,config: Config):
        super().__init__()
        self.config: Config = config
        self.dynamic_app_order: list[str] = []
        self.apps_bars: list[TaskbarAppsBar] = []

        screen_size = QGuiApplication.primaryScreen().size()

        self.setWindowTitle("taskbarPlus")
        self.setGeometry(0,screen_size.height()-self.config.theme.taskbar_height,screen_size.width(),self.config.theme.taskbar_height)
        self.setFixedSize(screen_size.width(),self.config.theme.taskbar_height)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        self.menu = QMenu(self)
        self.menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.config.theme.background};
                color: {self.config.theme.foreground};
                border: 1px solid {self.config.theme.foreground};
            }}
            QMenu::item {{
                padding: 8px;
                padding-right: 80px;
            }}
            QMenu::item:selected {{
                background-color: {self.config.theme.hover};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {self.config.theme.menu_separator_color};
            }}
        """)
        self.menu.addAction("Task Manager",lambda: launch_windows_app("taskmgr.exe"))
        self.menu.addSeparator()
        self.menu.addAction("Refresh",self.refresh_apps)
        self.menu.addAction("Exit",self.close)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda pos: self.menu.exec(self.mapToGlobal(pos)))

        central_widget = QWidget()
        central_widget.setObjectName("taskbarRoot")
        self.setCentralWidget(central_widget)

        texture_rule = ""
        if self.config.theme.taskbar_texture:
            texture_path = self.config.theme.taskbar_texture.replace("\\","/")
            if self.config.theme.taskbar_texture_mode == "stretch":
                texture_rule = f'border-image: url("{texture_path}") 0 0 0 0 stretch stretch;'
            elif self.config.theme.taskbar_texture_mode == "tile":
                texture_rule = f'background-image: url("{texture_path}"); background-repeat: repeat-xy;'

        central_widget.setStyleSheet(f"""
            QWidget#taskbarRoot {{
                background-color: {self.config.theme.background};
                color: {self.config.theme.foreground};
                {texture_rule}
            }}
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        central_widget.setLayout(layout)

        sections = [*self.config.layout.left,*self.config.layout.right]
        apps_items = self.build_taskbar_items() if "apps" in sections else []

        left_container = self.build_section(self.config.layout.left,apps_items)
        right_container = self.build_section(self.config.layout.right,apps_items)

        layout.addWidget(left_container)
        layout.addStretch()
        layout.addWidget(right_container)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_apps)
        self.timer.start(1500)

    def on_start_clicked(self):
        tap_key(win32con.VK_LWIN)
    
    def on_search_clicked(self):
        press_key(win32con.VK_LWIN)
        tap_key(ord("S"))
        release_key(win32con.VK_LWIN)

    def on_task_view_clicked(self):
        press_key(win32con.VK_LWIN)
        tap_key(win32con.VK_TAB)
        release_key(win32con.VK_LWIN)

    def open_network_settings(self):
        subprocess.run("explorer.exe ms-availablenetworks:",shell=True)

    def open_volume_settings(self):
        launch_windows_app("sndvol.exe")

    def build_section(self,sections: list[str],apps_items: list[TaskbarItem]) -> QWidget:
        container = QWidget()
        section_layout = QHBoxLayout()
        section_layout.setContentsMargins(0,0,0,0)
        section_layout.setSpacing(self.config.theme.gap)
        container.setLayout(section_layout)

        for section in sections:
            if section == "start":
                widget = self.create_button("start","Start",self.config.theme.start_icon,self.on_start_clicked)
            elif section == "search":
                widget = self.create_button("search","Search",self.config.theme.search_icon,self.on_search_clicked)
            elif section == "task_view":
                widget = self.create_button("task_view","Task View",self.config.theme.task_view_icon,self.on_task_view_clicked)
            elif section == "apps":
                widget = TaskbarAppsBar(apps_items,self.config)
                widget.itemClicked.connect(self.on_item_clicked)
                self.apps_bars.append(widget)
            elif section == "tray":
                tray_items = [
                    self.create_tray_icon("network","assets/network.png",self.open_network_settings),
                    self.create_tray_icon("volume","assets/volume.png",self.open_volume_settings)
                ]
                widget = TrayWidget(tray_items,self.config)
            elif section == "clock":
                widget = ClockWidget(self.config)
            elif section == "show_desktop":
                widget = ShowDesktopButton(self.config)
            else:
                continue

            section_layout.addWidget(widget)

        return container
    
    def create_tray_icon(self,icon_id: str,icon_path: str,handler) -> TrayIcon:
        button = TrayIcon(
            TrayItem(id=icon_id,icon=QIcon(icon_path)),
            self.config
        )
        button.clicked.connect(handler)
        return button

    def create_button(self,item_id: str,title: str,icon_theme,handler) -> TaskbarButton:
        button = TaskbarButton(
            TaskbarItem(
                id=item_id,
                title=title,
                icon=QIcon(icon_theme.default),
                hover_icon=QIcon(icon_theme.hover) if icon_theme.hover else None
            ),
            self.config
        )
        button.setToolTip(title)
        button.clicked.connect(handler)
        return button

    def normalize_path(self,path: str | None) -> str | None:
        if not path:
            return None
        return os.path.normcase(os.path.normpath(path))

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

        current_dynamic_ids = set(dynamic_items)
        stable_dynamic_order = [
            item_id for item_id in self.dynamic_app_order
            if item_id in current_dynamic_ids
        ]

        for item_id in dynamic_items:
            if item_id not in stable_dynamic_order:
                stable_dynamic_order.append(item_id)

        self.dynamic_app_order = stable_dynamic_order

        for item_id in stable_dynamic_order:
            items.append(dynamic_items[item_id])

        return items
    
    def refresh_apps(self):
        if not self.apps_bars:
            return

        items = self.build_taskbar_items()
        for apps_bar in self.apps_bars:
            apps_bar.set_items(items)

    def on_item_clicked(self,item: TaskbarItem,button: QWidget):
        count = len(item.windows)

        if count == 0:
            if item.launch_path:
                subprocess.Popen(item.launch_path)
        elif count == 1:
            hwnd = item.windows[0].hwnd
            self.activate_window(hwnd)
        else:
            self.show_windows_menu(item,button)

    def activate_window(self,hwnd: int):
        try:
            win32gui.ShowWindow(hwnd,win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            print("couldn't activate window:",e)

    def show_windows_menu(self,item: TaskbarItem,button: QWidget):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.config.theme.background};
                color: {self.config.theme.foreground};
            }}
            QMenu::item {{
                padding: 6px;
                padding-left: 2px;
            }}
            QMenu::item:selected {{
                background-color: {self.config.theme.hover};
            }}
        """)

        for window in item.windows:
            action = menu.addAction(window.title)
            action.triggered.connect(
                lambda checked=False,hwnd=window.hwnd: self.activate_window(hwnd)
            )

        new_win_action = menu.addAction("Open new window")
        new_win_action.setIcon(QIcon("assets/add.png").pixmap(15,15))
        new_win_action.triggered.connect(
            lambda checked=False,path=item.launch_path: subprocess.Popen(path) if path else None
        )

        pos = button.mapToGlobal(button.rect().topLeft())
        pos.setY(pos.y()-menu.sizeHint().height())
        menu.exec(pos)