from __future__ import annotations
import subprocess
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import win32con
from src.l18n import L18n
from src.shell import *
from src.config import Config
from src.models import *
from src.utils import menu_style,pixmap_dominant_color,theme_color
from threading import Thread

class TaskbarAppsBar(QWidget):
    itemClicked = Signal(object,object)
    appDropped = Signal(str)

    def __init__(self,items: list[TaskbarItem],config: Config,l18n: L18n):
        super().__init__()
        self.config = config
        self.l18n = l18n
        self.items = items
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(self.config.theme.gap)
        self.setLayout(self.layout)

        self.rebuild()

    def set_items(self,items: list[TaskbarItem]):
        self.items = items
        self.rebuild()

    def set_active_window(self,hwnd: int):
        for index,item in enumerate(self.items):
            item.active = any(window.hwnd == hwnd for window in item.windows)

            child = self.layout.itemAt(index)
            if child is None:
                continue

            button = child.widget()
            if button is not None:
                button.item.active = item.active
                button.update()

    def rebuild(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()

        for item in self.items:
            btn = TaskbarButton(item,self.config,self.l18n)
            tooltip = item.title
            if len(item.windows) > 1:
                tooltip = f"{item.title} ({len(item.windows)})"
            btn.setToolTip(tooltip)
            btn.clicked.connect(
                lambda checked=False,item=item,btn=btn: self.itemClicked.emit(item,btn)
            )
            btn.itemAction.connect(self.itemClicked.emit)
            self.layout.addWidget(btn)

        self.adjustSize()

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
    def __init__(self,config: Config,show_date=True,show_time=True):
        super().__init__()
        self.config = config
        self.show_date = show_date
        self.show_time = show_time
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"""
            color: {self.config.theme.foreground};
            padding: {self.config.theme.padding_y}px {self.config.theme.padding_x}px;
        """)
        self.update_time()

    def update_time(self):
        current_time = QTime.currentTime().toString(self.config.behavior.clock.time_format)
        current_date = QDate.currentDate().toString(self.config.behavior.clock.date_format)
        text = ""
        if self.show_time:
            text += current_time
        if self.show_date:
            if text:
                text += "\n"
            text += current_date
        self.setText(text)
        QTimer.singleShot(1000,self.update_time)

class TaskbarButton(QAbstractButton):
    itemAction = Signal(object,object)

    def __init__(self,item: TaskbarItem,config: Config,l18n: L18n,parent=None):
        super().__init__(parent)
        self.config = config
        self.l18n = l18n
        self.item = item
        self.icon = item.icon
        self.hover_icon = item.hover_icon
        self.active_icon = item.active_icon
        self.icon_pixmap = item.icon_pixmap
        self.hover_icon_pixmap = item.hover_icon_pixmap
        self.active_icon_pixmap = item.active_icon_pixmap
        self.dominant_hover_color = self.config.theme.hover
        self.hovered = False
        self.pressed = False
        self.bg_hover_progress = 0.0
        self.icon_hover_progress = 0.0
        self.indicator_hover_progress = 0.0

        self.button_style = self.config.theme.button_style
        self.button_spr = self.config.resolve_asset("assets/button_spr.png") #button spritesheet
        self.button_spr = QPixmap(self.button_spr) if self.button_spr else None

        if item.id != "start":
            dominant_hover_color = pixmap_dominant_color(
                self.icon.pixmap(self.config.theme.icon_size,self.config.theme.icon_size)
            )
            if dominant_hover_color != "#00000000":
                self.dominant_hover_color = dominant_hover_color

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        self.bg_anim = QPropertyAnimation(self,b"bgHoverProgress",self)
        self.bg_anim.setDuration(150)
        self.bg_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.icon_anim = QPropertyAnimation(self,b"iconHoverProgress",self)
        if item.id == "start":
            transition = getattr(self.config.theme,"start_icon_transition",{}) or {}
            self.icon_anim.setDuration(transition.get("duration",200))
            self.icon_anim.setEasingCurve(self.easing_curve(transition.get("easing"),QEasingCurve.OutCubic))
        else:
            self.icon_anim.setDuration(150)
            self.icon_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.indicator_anim = QPropertyAnimation(self,b"indicatorHoverProgress",self)
        self.indicator_anim.setDuration(150)
        self.indicator_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.setMouseTracking(True)
        if item.id == "start":
            self.setFixedSize(
                self.config.theme.start_button_width,
                self.config.theme.start_button_height
            )
        elif item.id == "search":
            self.setFixedSize(
                self.config.theme.search_button_width,
                self.config.theme.search_button_height
            )
        elif item.id == "task_view":
            self.setFixedSize(
                self.config.theme.task_view_button_width,
                self.config.theme.task_view_button_height
            )
        else:
            self.setFixedSize(
                self.config.theme.button_width,
                self.config.theme.button_height
            )

    def tr(self,key):
        return self.l18n.tr(key)

    def show_context_menu(self,pos):
        menu = QMenu(self)
        menu.setStyleSheet(menu_style(self.config))
        if self.item.windows:
            for window in self.item.windows:
                action = menu.addAction(window.title)
                action.triggered.connect(lambda checked=False,hwnd=window.hwnd: self.itemAction.emit(self.item,hwnd))
            menu.addSeparator()
        new_win_action = menu.addAction(self.tr("taskbar.menu.new_win"))
        new_win_action.setIcon(QIcon(self.config.resolve_asset("assets/add.png")).pixmap(15,15))
        new_win_action.triggered.connect(lambda: launch_windows_app(self.item.launch_path) if self.item.launch_path else None)
        pin_action = menu.addAction(self.tr("taskbar.menu.unpin" if self.item.pinned else "taskbar.menu.pin"))
        pin_action.setIcon(QIcon(self.config.resolve_asset("assets/pin.png")) if not self.item.pinned else QIcon(self.config.resolve_asset("assets/unpin.png")))
        pin_action.triggered.connect(lambda: self.itemAction.emit(self.item,"pin"))
        menu.exec(self.mapToGlobal(pos))

    def get_bg_hover_progress(self):
        return self.bg_hover_progress

    def set_bg_hover_progress(self,value):
        self.bg_hover_progress = float(value)
        self.update()

    bgHoverProgress = Property(float,get_bg_hover_progress,set_bg_hover_progress)

    def get_icon_hover_progress(self):
        return self.icon_hover_progress

    def set_icon_hover_progress(self,value):
        self.icon_hover_progress = float(value)
        self.update()

    iconHoverProgress = Property(float,get_icon_hover_progress,set_icon_hover_progress)

    def get_indicator_hover_progress(self):
        return self.indicator_hover_progress

    def set_indicator_hover_progress(self,value):
        self.indicator_hover_progress = float(value)
        self.update()

    indicatorHoverProgress = Property(float,get_indicator_hover_progress,set_indicator_hover_progress)

    def enterEvent(self,event):
        self.hovered = True

        self.bg_anim.stop()
        self.set_bg_hover_progress(1.0)

        self.icon_anim.stop()
        self.icon_anim.setStartValue(self.icon_hover_progress)
        self.icon_anim.setEndValue(1.0)
        self.icon_anim.start()

        self.indicator_anim.stop()
        self.indicator_anim.setStartValue(self.indicator_hover_progress)
        self.indicator_anim.setEndValue(1.0)
        self.indicator_anim.start()

        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.pressed = False

        self.bg_anim.stop()
        self.bg_anim.setStartValue(self.bg_hover_progress)
        self.bg_anim.setEndValue(0.0)
        self.bg_anim.start()

        self.icon_anim.stop()
        self.icon_anim.setStartValue(self.icon_hover_progress)
        self.icon_anim.setEndValue(0.0)
        self.icon_anim.start()

        self.indicator_anim.stop()
        self.indicator_anim.setStartValue(self.indicator_hover_progress)
        self.indicator_anim.setEndValue(0.0)
        self.indicator_anim.start()

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

    def mouseMoveEvent(self,event):
        if self.button_style == "win8" and self.hovered:
            self.update()
        super().mouseMoveEvent(event)

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        try:
            rect = self.rect()

            if self.button_style == "win10":
                self.draw_button_win10(painter,rect)
            elif self.button_style == "win8":
                self.draw_button_win8(painter,rect)

            #determine icon size
            if self.item.id == "start":
                icon_size = self.config.theme.start_icon_size
            elif self.item.id == "search":
                icon_size = self.config.theme.search_icon_size
            elif self.item.id == "task_view":
                icon_size = self.config.theme.task_view_icon_size
            else:
                icon_size = self.config.theme.icon_size
                
            if self.item.id == "start" and self.icon_pixmap is not None:
                pix_default = self.scaled_start_pixmap(self.icon_pixmap,rect,icon_size)
            else:
                pix_default = self.icon.pixmap(icon_size,icon_size)

            x = (rect.width()-pix_default.width())//2
            y = (rect.height()-pix_default.height())//2

            if (self.pressed or self.item.active) and self.active_icon:
                painter.setOpacity(self.config.theme.icon_opacity)
                if self.item.id == "start" and self.active_icon_pixmap is not None:
                    painter.drawPixmap(x,y,self.scaled_start_pixmap(self.active_icon_pixmap,rect,icon_size))
                else:
                    painter.drawPixmap(x,y,self.active_icon.pixmap(icon_size,icon_size))
            elif self.hover_icon:
                if self.item.id == "start" and self.hover_icon_pixmap is not None:
                    pix_hover = self.scaled_start_pixmap(self.hover_icon_pixmap,rect,icon_size)
                else:
                    pix_hover = self.hover_icon.pixmap(icon_size,icon_size)

                painter.setOpacity((1.0-self.icon_hover_progress)*self.config.theme.icon_opacity)
                painter.drawPixmap(x,y,pix_default)

                painter.setOpacity(self.icon_hover_progress*self.config.theme.icon_opacity)
                painter.drawPixmap(x,y,pix_hover)

                painter.setOpacity(self.config.theme.icon_opacity)
            else:
                painter.setOpacity(self.config.theme.icon_opacity)
                painter.drawPixmap(x,y,pix_default)
        finally:
            painter.end()

    def easing_curve(self,name: str | None,default):
        if not name:
            return default

        easing_type = getattr(QEasingCurve.Type,name,None)
        if easing_type is None:
            easing_type = getattr(QEasingCurve,name,None)
        return easing_type if easing_type is not None else default

    def scaled_start_pixmap(self,pixmap: QPixmap,rect: QRect,icon_size: int) -> QPixmap:
        if pixmap.isNull():
            return pixmap

        if pixmap.width() == pixmap.height():
            return pixmap.scaled(icon_size,icon_size,Qt.KeepAspectRatio,Qt.SmoothTransformation)

        return pixmap.scaled(rect.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation)

    def draw_indicator(self, painter: QPainter, rect: QRect):
        if not self.item.running:
            return

        reference_button_width = 48

        def scale_width(value: float) -> int:
            return max(1, round(rect.width()*value/reference_button_width))

        def lerp(a: float,b: float,t: float) -> float:
            return a+(b-a)*t

        indicator_h = max(1, round(rect.height()*2/30))
        indicator_y = rect.height()-indicator_h
        center_x = rect.width()//2

        color = theme_color(self.config.theme.accent)

        darker_color = QColor(color)
        darker_color = darker_color.darker(140)

        t = self.indicator_hover_progress
        window_count = len(self.item.windows)

        if window_count <= 1:
            w = scale_width(lerp(36, 44, t))
            x = center_x - w // 2
            painter.fillRect(x, indicator_y, w, indicator_h, color)
        else:
            main_w = scale_width(lerp(25, 40, t))
            gap = scale_width(1)
            secondary_w = scale_width(lerp(12, 6, t))

            total_w = main_w + gap + secondary_w
            start_x = center_x - total_w // 2

            painter.fillRect(start_x, indicator_y, main_w, indicator_h, color)
            painter.fillRect(start_x + main_w + gap, indicator_y, secondary_w, indicator_h, darker_color)

    def draw_button_win10(self,painter: QPainter,rect: QRect):
        #define background color
        base_bg = theme_color(self.config.theme.background)

        if self.item.id == "start" and not self.config.theme.start_button_fx:
            painter.fillRect(rect,base_bg)
            return

        hover_bg = theme_color(
            self.config.theme.start_button_hover
            if self.item.id == "start"
            else self.config.theme.hover
        )

        active_bg = theme_color(
            self.config.theme.start_button_active
            if self.item.id == "start"
            else self.config.theme.active
        )

        painter.fillRect(rect,base_bg)

        if self.item.active or self.pressed:
            painter.fillRect(rect,active_bg)
        elif self.bg_hover_progress > 0.0:
            hover = QColor(hover_bg)
            hover.setAlphaF(hover.alphaF()*self.bg_hover_progress)
            painter.fillRect(rect,hover)

        self.draw_indicator(painter,rect)

    def draw_button_win8(self,painter: QPainter,rect: QRect):
        #define background color
        window_count = len(self.item.windows)

        base_bg = theme_color(self.config.theme.background)

        hover_bg = theme_color(
            self.config.theme.start_button_hover
            if self.item.id == "start"
            else self.config.theme.hover
        )

        active_bg = theme_color(
            self.config.theme.start_button_active
            if self.item.id == "start"
            else self.config.theme.active
        )

        painter.fillRect(rect,base_bg)

        if self.item.id == "start" and not self.config.theme.start_button_fx:
            return

        border_color = theme_color(self.config.theme.active).lighter(200)

        is_open_app = window_count > 0
        is_active_state = is_open_app

        if is_active_state:
            painter.fillRect(rect,active_bg)

            painter.setPen(QPen(border_color,1))
            painter.drawRect(rect.adjusted(0,0,-0.5,-0.5))

        if self.bg_hover_progress > 0.0:
            if not is_open_app: #hovering and not opened
                if self.button_spr and not self.button_spr.isNull():
                    painter.save()
                    if self.bg_hover_progress < 1.0:
                        painter.setOpacity(self.bg_hover_progress)
                    idx = 8 if not self.pressed else 9 #sprite idx
                    sprite_rect = QRect(0,idx*40,60,40)
                    painter.drawPixmap(rect,self.button_spr,sprite_rect)
                    painter.restore()
                else:
                    hover = QColor(hover_bg)
                    hover.setAlphaF(hover.alphaF()*self.bg_hover_progress)
                    painter.fillRect(rect,hover)

                    hover_border_color = QColor(border_color)
                    hover_border_color.setAlphaF(hover_border_color.alphaF()*self.bg_hover_progress)
                    painter.setPen(QPen(hover_border_color,1))
                    painter.drawRect(rect.adjusted(0,0,-0.5,-0.5)) #border
            else:
                #draw hot track effect
                mouse_x = self.mapFromGlobal(QCursor.pos()).x()
                mouse_y = self.mapFromGlobal(QCursor.pos()).y()
                radius = max(rect.width(),rect.height())*1.6
                hot_track_color = QColor(self.dominant_hover_color).lighter(180)

                center = QColor(hot_track_color)
                center.setAlphaF(min(1.0,0.75*self.bg_hover_progress))
                middle = QColor(hot_track_color)
                middle.setAlphaF(min(1.0,0.28*self.bg_hover_progress))
                edge = QColor(hot_track_color)
                edge.setAlpha(0)

                gradient = QRadialGradient(QPointF(mouse_x,mouse_y),radius)
                gradient.setColorAt(0.0,center)
                gradient.setColorAt(0.35,middle)
                gradient.setColorAt(1.0,edge)

                painter.save()
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(gradient))
                painter.drawEllipse(QPointF(mouse_x,mouse_y),radius,radius)
                painter.restore()

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

        try:
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
        finally:
            painter.end()
    
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
        self.collapsed = False
        self.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(self.config.theme.tray_gap)
        self.setLayout(self.layout)
        self.rebuild()

    def set_items(self,items: list[TrayIcon]):
        self.items = items
        if not self.collapsed:
            self.rebuild()

    def rebuild(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
                
        for item in self.items:
            item.clicked.connect(
                lambda checked=False,item=item.item: self.itemClicked.emit(item)
            )
            item.rightClicked.connect(self.itemRightClicked.emit)
            self.layout.addWidget(item)

        self.adjustSize()
        self.updateGeometry()
        if self.parentWidget() is not None:
            self.parentWidget().updateGeometry()

    def set_collapsed(self,collapsed: bool):
        if self.collapsed == collapsed:
            return

        self.collapsed = collapsed
        if self.collapsed:
            self.setVisible(False)
        else:
            self.rebuild()
            self.setVisible(True)

        self.updateGeometry()
        if self.parentWidget() is not None:
            self.parentWidget().updateGeometry()

    def toggle_collapsed(self):
        self.set_collapsed(not self.collapsed)

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

        try:
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
        finally:
            painter.end()

class SearchBox(QLineEdit):
    def __init__(self,config: Config,l18n: L18n):
        super().__init__()
        self.config = config
        self.l18n = l18n

        self.search_icon = QIcon()
        search_icon_path = self.config.resolve_asset(self.config.theme.search_icon)
        if search_icon_path:
            self.search_icon = QIcon(search_icon_path)

        self.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        self.setFixedSize(
            self.config.theme.search_box_width+self.config.theme.padding_x*2,
            self.config.theme.search_box_height
        )
        self.setClearButtonEnabled(self.config.behavior.search.box_clear_button)

        icon_size = self.config.theme.search_icon_size
        icon_gap = self.config.theme.padding_x
        left_padding = self.config.theme.padding_x+icon_size+icon_gap-10

        self.setStyleSheet(f"""
            background-color: {self.config.theme.search_box_background};
            color: {self.config.theme.search_box_foreground};
            border: none;
            font-size: 16px;
            padding-top: {self.config.theme.padding_y}px;
            padding-bottom: {self.config.theme.padding_y}px;
            padding-right: {self.config.theme.padding_x}px;
            padding-left: {left_padding}px;
        """)

        if self.config.theme.search_box_height >= 35:
            self.placeholder_value = self.tr("taskbar.search.placeholder")
        else:
            self.placeholder_value = self.tr("taskbar.search.placeholder_short")

        self.placeholder_color = QColor("#333333")

        font = self.font()
        font.setLetterSpacing(QFont.AbsoluteSpacing,0)
        self.setFont(font)

    def tr(self,key):
        return self.l18n.tr(key)

    def focusInEvent(self,event):
        super().focusInEvent(event)
        if self.config.behavior.search.engine == "windows_search":
            self.launch_search("")

    def focusOutEvent(self,event):
        self.clear()
        super().focusOutEvent(event)

    def keyPressEvent(self,event):
        if event.key() == Qt.Key_Escape:
            self.clear()
            self.clearFocus()
            event.accept()
            return
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            query = self.text().strip()
            if query:
                self.launch_search(query)
            self.clear()
            self.clearFocus()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self,event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        try:
            icon_size = self.config.theme.search_icon_size

            if not self.search_icon.isNull():
                pix = self.search_icon.pixmap(icon_size,icon_size)
                painter.drawPixmap(4,(self.height()-pix.height())//2,pix)

            if not self.text() and not self.hasFocus() and self.placeholder_value:
                painter.setPen(self.placeholder_color)

                text_x = self.config.theme.padding_x+icon_size+self.config.theme.padding_x-8
                text_rect = QRect(
                    text_x,-1,
                    self.width()-text_x-self.config.theme.padding_x,
                    self.height()
                )

                painter.drawText(
                    text_rect,
                    Qt.AlignVCenter | Qt.AlignLeft,
                    self.placeholder_value
                )
        finally:
            painter.end()

    def launch_search(self,query=""):
        if self.config.behavior.search.engine == "everything":
            thread = Thread(
                target=lambda: subprocess.run(
                    f'"{self.config.behavior.search.everything_path}" -search "{query}"',
                    shell=True
                )
            )
            thread.start()
        elif self.config.behavior.search.engine == "windows_search":
            self.clearFocus()
            press_key(win32con.VK_LWIN)
            tap_key(ord("S"))
            release_key(win32con.VK_LWIN)

class TrayCollapseButton(QAbstractButton):
    def __init__(self,config: Config,parent=None):
        super().__init__(parent)
        self.config = config
        self.hovered = False
        self.pressed = False
        self.collapsed = False

        self.expanded_icon = QIcon(self.config.resolve_asset("assets/chevron-right.png"))
        self.collapsed_icon = QIcon(self.config.resolve_asset("assets/chevron-left.png"))
        self.icon = self.expanded_icon

        self.setMouseTracking(True)
        self.setFixedSize(
            self.config.theme.tray_icon_size+self.config.theme.padding_x,
            self.config.theme.button_height
        )

    def set_collapsed(self,collapsed: bool):
        self.collapsed = collapsed
        self.icon = self.collapsed_icon if self.collapsed else self.expanded_icon
        self.update()

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

        try:
            rect = self.rect()

            bg = theme_color(self.config.theme.background)
            if self.pressed:
                bg = theme_color(self.config.theme.active)
            elif self.hovered:
                bg = theme_color(self.config.theme.hover)

            painter.fillRect(rect,bg)

            icon_size = self.config.theme.tray_icon_size
            pix = self.icon.pixmap(icon_size,icon_size)
            x = (rect.width()-pix.width())//2
            y = (rect.height()-pix.height())//2
            painter.drawPixmap(x,y,pix)
        finally:
            painter.end()
