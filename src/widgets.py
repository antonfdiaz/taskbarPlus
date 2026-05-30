from __future__ import annotations
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import win32con
from src.shell import *
from src.config import Config
from src.models import *
from src.utils import menu_style,theme_color

class TaskbarAppsBar(QWidget):
    itemClicked = Signal(object,object)
    appDropped = Signal(str)

    def __init__(self,items: list[TaskbarItem],config: Config):
        super().__init__()
        self.config = config
        self.items = items
        self.setAcceptDrops(True)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(self.config.theme.gap)
        self.setLayout(self.layout)

        self.rebuild()

    def set_items(self,items: list[TaskbarItem]):
        self.items = items
        self.rebuild()

    def rebuild(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()

        for item in self.items:
            btn = TaskbarButton(item,self.config)
            tooltip = item.title
            if len(item.windows) > 1:
                tooltip = f"{item.title} ({len(item.windows)})"
            btn.setToolTip(tooltip)
            btn.clicked.connect(
                lambda checked=False,item=item,btn=btn: self.itemClicked.emit(item,btn)
            )
            btn.itemAction.connect(self.itemClicked.emit)
            self.layout.addWidget(btn)

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self,event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.appDropped.emit(path)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

class ClockWidget(QLabel):
    def __init__(self,config: Config):
        super().__init__()
        self.config = config
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"""
            color: {self.config.theme.foreground};
            padding: {self.config.theme.padding_y}px {self.config.theme.padding_x}px;
        """)
        self.update_time()

    def update_time(self):
        current_time = QTime.currentTime().toString(self.config.theme.clock_format)
        current_date = QDate.currentDate().toString(self.config.theme.date_format)
        self.setText(current_time+"\n"+current_date)
        QTimer.singleShot(1000,self.update_time)

class TaskbarButton(QAbstractButton):
    itemAction = Signal(object,object)

    def __init__(self,item: TaskbarItem,config: Config,parent=None):
        super().__init__(parent)
        self.config = config
        self.item = item
        self.icon = item.icon
        self.hover_icon = item.hover_icon
        self.active_icon = item.active_icon
        self.hovered = False
        self.pressed = False
        self.hover_progress = 0.0

        #context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        if self.item.id == "start":
            self.icon_anim = QPropertyAnimation(self,b"hoverProgress",self)
            transition = getattr(self.config.theme, "start_icon_transition",{}) or {}
            self.icon_anim.setDuration(transition.get("duration",200))
            easing_name = transition.get("easing","InOutQuad")
            self.icon_anim.setEasingCurve(getattr(QEasingCurve,easing_name,QEasingCurve.InOutQuad))
        else:
            self.icon_anim = QPropertyAnimation(self,b"hoverProgress",self)
            self.icon_anim.setDuration(0)

        self.setMouseTracking(True)
        self.setFixedSize(
            self.config.theme.button_width,
            self.config.theme.button_height
        )

    def show_context_menu(self,pos):
        menu = QMenu(self)
        menu.setStyleSheet(menu_style(self.config))
        if self.item.windows:
            for window in self.item.windows:
                action = menu.addAction(window.title)
                action.triggered.connect(lambda checked=False,hwnd=window.hwnd: self.itemAction.emit(self.item,hwnd))
            menu.addSeparator()
        new_win_action = menu.addAction("Open new window")
        new_win_action.setIcon(QIcon("assets/add.png").pixmap(15,15))
        new_win_action.triggered.connect(lambda: launch_windows_app(self.item.launch_path) if self.item.launch_path else None)
        pin_action = menu.addAction("Unpin from taskbar" if self.item.pinned else "Pin to taskbar")
        pin_action.setIcon(QIcon("assets/pin.png") if not self.item.pinned else QIcon("assets/unpin.png"))
        pin_action.triggered.connect(lambda: self.itemAction.emit(self.item,"pin"))
        menu.exec(self.mapToGlobal(pos))

    def get_hover_progress(self):
        return self.hover_progress

    def set_hover_progress(self,value):
        self.hover_progress = float(value)
        self.update()

    hoverProgress = Property(float,get_hover_progress,set_hover_progress)

    def enterEvent(self,event):
        self.hovered = True
        if self.hover_icon:
            self.icon_anim.stop()
            self.icon_anim.setStartValue(self.hover_progress)
            self.icon_anim.setEndValue(1.0)
            self.icon_anim.start()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self,event):
        self.hovered = False
        self.pressed = False
        if self.hover_icon:
            self.icon_anim.stop()
            self.icon_anim.setStartValue(self.hover_progress)
            self.icon_anim.setEndValue(0.0)
            self.icon_anim.start()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self,event):
        if event.button() == Qt.LeftButton:
            self.pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self,event):
        self.pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        try:
            rect = self.rect()

            bg = theme_color(self.config.theme.background)
            if self.pressed:
                bg = theme_color(self.config.theme.active)
            elif self.hovered:
                bg = theme_color(self.config.theme.hover)
            elif self.item.active:
                bg = theme_color(self.config.theme.active)

            painter.fillRect(rect,bg)

            if self.item.id == "start":
                icon_size = self.config.theme.start_icon_size
            elif self.item.id == "search":
                icon_size = self.config.theme.search_icon_size
            elif self.item.id == "task_view":
                icon_size = self.config.theme.task_view_icon_size
            else:
                icon_size = self.config.theme.icon_size
                
            pix_default = self.icon.pixmap(icon_size,icon_size)
            x = (rect.width()-pix_default.width())//2
            y = (rect.height()-pix_default.height())//2

            if (self.pressed or self.item.active) and self.active_icon:
                painter.setOpacity(self.config.theme.icon_opacity)
                painter.drawPixmap(x,y,self.active_icon.pixmap(icon_size,icon_size))
            elif self.hover_icon:
                pix_hover = self.hover_icon.pixmap(icon_size,icon_size)

                painter.setOpacity((1.0-self.hover_progress)*self.config.theme.icon_opacity)
                painter.drawPixmap(x,y,pix_default)

                painter.setOpacity(self.hover_progress*self.config.theme.icon_opacity)
                painter.drawPixmap(x,y,pix_hover)

                painter.setOpacity(self.config.theme.icon_opacity)
            else:
                painter.setOpacity(self.config.theme.icon_opacity)
                painter.drawPixmap(x,y,pix_default)

            self.draw_indicator(painter,rect)
        finally:
            painter.end()

    def draw_indicator(self,painter: QPainter,rect: QRect):
        if not self.item.running:
            return

        indicator_h = 2
        indicator_y = rect.height()-indicator_h

        color = theme_color(self.config.theme.accent)
        darker_color = "#"+"".join(
            f"{max(0, int(int(self.config.theme.accent[i:i+2],16)*0.7)):02x}"
            for i in (1,3,5)
        )

        window_count = len(self.item.windows)

        if window_count <= 1:
            if self.hovered:
                painter.fillRect(rect.width()//2-22,indicator_y,44,indicator_h,color)
            else:
                painter.fillRect(rect.width()//2-18,indicator_y,36,indicator_h,color)
        else:
            if self.hovered:
                painter.fillRect(rect.width()//2-25,indicator_y,40,indicator_h,color)
                painter.fillRect(rect.width()//2+16,indicator_y,6,indicator_h,darker_color)
            else:
                painter.fillRect(rect.width()//2-19,indicator_y,25,indicator_h,color)
                painter.fillRect(rect.width()//2+7,indicator_y,12,indicator_h,darker_color)

class ShowDesktopButton(QAbstractButton):
    def __init__(self,config: Config,parent=None):
        super().__init__(parent)
        self.config = config
        self.hovered = False
        self.pressed = False

        self.setMouseTracking(True)
        self.setFixedSize(
            self.config.theme.show_desktop_width,
            self.config.theme.button_height
        )

    def enterEvent(self,event):
        self.hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self,event):
        self.hovered = False
        self.pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self,event):
        if event.button() == Qt.LeftButton:
            self.pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self,event):
        self.pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        bg = theme_color(self.config.theme.background)
        if self.pressed:
            bg = theme_color(self.config.theme.active)
        elif self.hovered:
            bg = theme_color(self.config.theme.hover)

        painter.fillRect(rect,bg)

        #draw border on the left side
        painter.setPen(QPen(theme_color(self.config.theme.show_desktop_border_color),1))
        painter.drawLine(rect.topLeft(),rect.bottomLeft())
    
    def mouseReleaseEvent(self,event):
        if event.button() == Qt.LeftButton:
            press_key(win32con.VK_LWIN)
            tap_key(ord("D"))
            release_key(win32con.VK_LWIN)
        super().mouseReleaseEvent(event)

class TrayWidget(QWidget):
    itemClicked = Signal(object)
    itemRightClicked = Signal(object)

    def __init__(self,items: list[TrayIcon],config: Config):
        super().__init__()
        self.config = config
        self.setFixedHeight(self.config.theme.taskbar_height)
        self.setStyleSheet(f"""
            background-color: {self.config.theme.background};
            color: {self.config.theme.foreground};
        """)

        self.items = items
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(self.config.theme.tray_gap)
        self.setLayout(self.layout)
        self.rebuild()

    def set_items(self,items: list[TrayIcon]):
        self.items = items
        self.rebuild()

    def rebuild(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()
                
        for item in self.items:
            item.clicked.connect(
                lambda checked=False,item=item.item: self.itemClicked.emit(item)
            )
            item.rightClicked.connect(self.itemRightClicked.emit)
            self.layout.addWidget(item)

class TrayIcon(QAbstractButton):
    rightClicked = Signal(object)

    def __init__(self,item: TrayItem,config: Config,parent=None):
        super().__init__(parent)
        self.item = item
        self.icon = item.icon
        self.hover_icon = item.hover_icon
        self.config = config
        self.hovered = False
        self.pressed = False

        self.setMouseTracking(True)
        self.setFixedSize(
            self.config.theme.tray_icon_size+self.config.theme.padding_x,
            self.config.theme.button_height
        )
        if item.tooltip:
            self.setToolTip(item.tooltip)

    def enterEvent(self,event):
        self.hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self,event):
        self.hovered = False
        self.pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self,event):
        if event.button() == Qt.LeftButton:
            self.pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self,event):
        self.pressed = False
        self.update()
        anchor = self.mapToGlobal(event.position().toPoint())
        self.item.anchor_x = anchor.x()
        self.item.anchor_y = anchor.y()

        if event.button() == Qt.RightButton:
            self.rightClicked.emit(self.item)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        bg = theme_color(self.config.theme.background)
        if self.pressed:
            bg = theme_color(self.config.theme.active)
        elif self.hovered:
            bg = theme_color(self.config.theme.hover)

        painter.fillRect(rect,bg)

        icon_size = self.config.theme.tray_icon_size
        icon = self.hover_icon if self.hovered and self.hover_icon else self.icon
        pix = icon.pixmap(icon_size,icon_size)

        x = (rect.width()-pix.width())//2
        y = (rect.height()-pix.height())//2
        painter.drawPixmap(x,y,pix)
