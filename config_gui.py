import json
import ctypes
from ctypes import wintypes
from pathlib import Path
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from src.config import Config

try:
    import win32con
    import win32gui
except ImportError:
    win32con = None
    win32gui = None

SECTIONS = ("theme","layout","apps")
SIDEBAR_WIDTH = 300
SIDEBAR_COLOR = "#e6e6e6"
OPTIONS = {
    "taskbar_texture_mode": ("stretch","tile"),
}
SCROLLBAR_STYLE = """
    QScrollBar:vertical {
        width: 12px;
        margin: 0;
        border: 0;
        background: transparent;
    }
    QScrollBar::handle:vertical {
        min-height: 36px;
        border: 0;
        background: #8f8f8f;
    }
    QScrollBar::handle:vertical:hover {
        background: #6f6f6f;
    }
    QScrollBar::handle:vertical:pressed {
        background: #555555;
    }
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {
        height: 0;
        border: 0;
        background: transparent;
    }
    QScrollBar:horizontal {
        height: 12px;
        margin: 0;
        border: 0;
        background: transparent;
    }
    QScrollBar::handle:horizontal {
        min-width: 36px;
        border: 0;
        background: #8f8f8f;
    }
    QScrollBar::handle:horizontal:hover {
        background: #6f6f6f;
    }
    QScrollBar::handle:horizontal:pressed {
        background: #555555;
    }
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {
        width: 0;
        border: 0;
        background: transparent;
    }
"""

DWMWA_NCRENDERING_POLICY = 2
DWMNCRP_ENABLED = 2
WM_NCCALCSIZE = 0x0083

def default_windows_qt_style():
    available = {name.lower(): name for name in QStyleFactory.keys()}
    for name in ("windows11","windowsvista","fusion"):
        if name in available:
            return QStyleFactory.create(available[name])
    return None

class POINT(ctypes.Structure):
    _fields_ = [
        ("x",wintypes.LONG),
        ("y",wintypes.LONG),
    ]

class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd",wintypes.HWND),
        ("message",wintypes.UINT),
        ("wParam",wintypes.WPARAM),
        ("lParam",wintypes.LPARAM),
        ("time",wintypes.DWORD),
        ("pt",POINT),
    ]

class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth",ctypes.c_int),
        ("cxRightWidth",ctypes.c_int),
        ("cyTopHeight",ctypes.c_int),
        ("cyBottomHeight",ctypes.c_int),
    ]

def enable_dwm_frame(hwnd: int):
    if win32con is None or win32gui is None:
        return

    style = win32gui.GetWindowLong(hwnd,win32con.GWL_STYLE)
    style |= (
        win32con.WS_CAPTION
        | win32con.WS_THICKFRAME
        | win32con.WS_SYSMENU
        | win32con.WS_MINIMIZEBOX
        | win32con.WS_MAXIMIZEBOX
    )
    win32gui.SetWindowLong(hwnd,win32con.GWL_STYLE,style)

    policy = ctypes.c_int(DWMNCRP_ENABLED)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(
        wintypes.HWND(hwnd),
        DWMWA_NCRENDERING_POLICY,
        ctypes.byref(policy),
        ctypes.sizeof(policy),
    )

    margins = MARGINS(1,1,1,1)
    ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
        wintypes.HWND(hwnd),
        ctypes.byref(margins),
    )

    win32gui.SetWindowPos(
        hwnd,
        None,
        0,
        0,
        0,
        0,
        win32con.SWP_NOMOVE
        | win32con.SWP_NOSIZE
        | win32con.SWP_NOZORDER
        | win32con.SWP_NOOWNERZORDER
        | win32con.SWP_FRAMECHANGED,
    )

class UwpToggle(QCheckBox):
    def __init__(self, checked=False):
        super().__init__()
        self.setChecked(checked)
        self.setFixedSize(self.sizeHint())

    def sizeHint(self):
        return QSize(46,22)

    def hitButton(self,pos):
        return self.rect().contains(pos)

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        checked = self.isChecked()
        hovered = self.underMouse()
        track = self.rect().adjusted(1,1,-1,-1)
        track_color = QColor("#0078d4" if checked else "#ffffff")
        border_color = QColor("#0078d4" if checked else "#333333")
        knob_color = QColor("#ffffff" if checked else "#333333")
        if hovered:
            track_color = track_color.lighter(120) if checked else track_color.darker(110)
            border_color = border_color.lighter(120) if checked else border_color.darker(110)
            knob_color = knob_color.lighter(120) if checked else knob_color.darker(110)

        painter.setPen(QPen(border_color, 2))
        painter.setBrush(track_color)
        painter.drawRoundedRect(track, 10, 10)

        knob_size = 12
        knob_x = track.right()-knob_size-3 if checked else track.left() + 4
        knob_y = track.center().y()-knob_size//2+1

        painter.setPen(Qt.NoPen)
        painter.setBrush(knob_color)
        painter.drawEllipse(knob_x, knob_y, knob_size, knob_size)

class UwpComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(34)
        self.setView(QListView())
        self.view().setStyleSheet("""
            QListView {
                border: 1px solid #9a9a9a;
                background: #ffffff;
                outline: 0;
            }
            QListView::item {
                min-height: 32px;
                padding: 5px 10px;
            }
            QListView::item:hover,
            QListView::item:selected {
                background: #a6d8ff;
                color: #000000;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        border = QColor("#0078d4" if self.hasFocus() else "#8a8a8a")

        painter.setPen(QPen(border, 2))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(rect)

        text_rect = rect.adjusted(10, 0, -34, 0)
        painter.setPen(QColor("#111111"))
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.currentText())

        arrow_x = rect.right() - 20
        arrow_y = rect.center().y() - 2
        painter.setPen(QPen(QColor("#666666"), 1.4))
        painter.drawLine(arrow_x - 5, arrow_y, arrow_x, arrow_y + 5)
        painter.drawLine(arrow_x, arrow_y + 5, arrow_x + 5, arrow_y)

class UwpSpinBox(QSpinBox):
    def __init__(self):
        super().__init__()
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.setFixedHeight(34)

class UwpDoubleSpinBox(QDoubleSpinBox):
    def __init__(self):
        super().__init__()
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.setFixedHeight(34)

class UwpButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setFixedHeight(32)
        self.setMinimumWidth(74)

    def sizeHint(self):
        return QSize(max(74, self.fontMetrics().horizontalAdvance(self.text()) + 28), 32)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        scale = 0.96 if self.isDown() else 1.0
        width = self.width() * scale
        height = self.height() * scale
        rect = QRectF(
            (self.width() - width) / 2,
            (self.height() - height) / 2,
            width,
            height,
        )

        if self.isDown():
            color = QColor("#b8b8b8")
        else:
            color = QColor("#d6d6d6")

        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRect(rect)

        #draw border on hover
        if self.underMouse() and not self.isDown():
            painter.setPen(QPen(QColor("#888888"),4))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

        painter.setPen(QColor("#000000"))
        painter.drawText(rect,Qt.AlignCenter,self.text())

class TitleBarButton(QAbstractButton):
    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.setFixedSize(46, 32)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self,event):
        self.update()

    def paintEvent(self,event):
        painter = QPainter(self)

        if self.underMouse():
            painter.fillRect(self.rect(),QColor("#e81123" if self.kind == "close" else "#e5e5e5"))

        if self.isDown():
            painter.fillRect(self.rect(),QColor("#ff6666" if self.kind == "close" else "#ccc"))

        color = QColor("#ffffff" if self.kind == "close" and self.underMouse() and not self.isDown() else "#111111")
        painter.setPen(QPen(color, 1, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))

        cx = self.width() // 2
        cy = self.height() // 2

        if self.kind == "minimize":
            painter.drawLine(cx - 5, cy, cx + 5, cy)
        elif self.kind == "maximize":
            painter.drawRect(cx - 5, cy - 5, 9, 9)
        elif self.kind == "restore":
            painter.drawRect(cx - 6, cy - 2, 8, 8)
            painter.drawRect(cx - 2, cy - 6, 8, 8)
        elif self.kind == "close":
            painter.drawLine(cx - 5, cy - 5, cx + 5, cy + 5)
            painter.drawLine(cx + 5, cy - 5, cx - 5, cy + 5)

class TitleBar(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.drag_pos = None
        self.setFixedHeight(32)
        self.setStyleSheet("background: transparent;")

        title = QLabel(window.windowTitle())
        title.setStyleSheet("background: transparent; padding-left: 10px; font-size: 12px;")

        self.minimize_button = TitleBarButton("minimize")
        self.maximize_button = TitleBarButton("maximize")
        self.close_button = TitleBarButton("close")

        self.minimize_button.clicked.connect(window.showMinimized)
        self.maximize_button.clicked.connect(self.toggle_maximized)
        self.close_button.clicked.connect(window.close)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(0, 0, SIDEBAR_WIDTH, self.height(), QColor(SIDEBAR_COLOR))
        painter.fillRect(SIDEBAR_WIDTH, 0, self.width() - SIDEBAR_WIDTH, self.height(), QColor("#ffffff"))

    def toggle_maximized(self):
        if self.window.isMaximized():
            self.window.showNormal()
            self.maximize_button.kind = "maximize"
        else:
            self.window.showMaximized()
            self.maximize_button.kind = "restore"
        self.maximize_button.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_maximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None and event.buttons() & Qt.LeftButton:
            if self.window.isMaximized():
                self.toggle_maximized()
                self.drag_pos = QPoint(self.window.width() // 2, 16)
            self.window.move(event.globalPosition().toPoint() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

class ConfigGui(QWidget):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.nullable = self.find_nullable_fields()
        self.dwm_frame_enabled = False
        self.default_qt_style = default_windows_qt_style()

        self.setObjectName("configRoot")
        self.setWindowTitle("taskbarPlus Config")
        self.setMinimumSize(880,560)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        if self.default_qt_style is not None:
            self.setStyle(self.default_qt_style)

        self.setStyleSheet("""
            QWidget {
                font-family: "Segoe UI",sans-serif;
                font-size: 14px;
            }
            QWidget#configRoot,
            QWidget#page {
                background-color: #fff;
            }
            QWidget#sidebar {
                background-color: """+SIDEBAR_COLOR+""";
            }
            QLabel#appTitle {
                background-color: transparent;
                font-size: 18px;
                font-weight: 300;
            }
            QLabel#pageTitle {
                font-size: 30px;
                font-weight: 300;
                margin-bottom: 18px;
            }
            QLabel#fieldLabel {
                font-size: 13px;
            }
            QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QPlainTextEdit {
                min-height: 28px;
                padding: 4px 8px;
                border: 2px solid #9a9a9a;
                background-color: #ffffff;
            }
            QLineEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus,QPlainTextEdit:focus {
                border-color: #0078d4;
            }
            QListWidget {
                border: 0;
                outline: 0;
                background-color: transparent;
            }
            QListWidget::item {
                min-height: 44px;
                padding-left: 16px;
                color: #111111;
            }
            QListWidget::item:hover {
                background-color: rgba(0,0,0,25);
            }
            QListWidget::item:selected {
                border-left: 4px solid #0078d4;
                color: #000000;
            }
            QScrollArea {
                border: 0;
            }
            UwpComboBox {
                border: 0;
                padding: 0;
            }
            QPushButton {
                min-width: 60px;
                padding: 4px 8px;
                background-color: #d6d6d6;
                border: none;
            }
            QPushButton:hover {
                border: 2px solid #888;
            }
            QPushButton:pressed {
                background-color: #b8b8b8;
                border: none;
            }
        """)

        self.pages = QStackedWidget()
        self.nav = QListWidget()

        for name in SECTIONS:
            self.nav.addItem(name.title())
            self.pages.addWidget(self.section_page(name))

        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)

        content = QHBoxLayout()
        content.setContentsMargins(0,0,0,0)
        content.setSpacing(0)
        content.addWidget(self.sidebar())
        content.addWidget(self.pages,1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(0)
        root.addWidget(TitleBar(self))
        root.addLayout(content,1)

    def showEvent(self,event):
        super().showEvent(event)
        if self.dwm_frame_enabled:
            return

        try:
            enable_dwm_frame(int(self.winId()))
            self.dwm_frame_enabled = True
        except Exception as error:
            print("couldn't enable config window DWM frame:",error)

    def nativeEvent(self,event_type,message):
        try:
            msg = MSG.from_address(int(message))
        except Exception:
            return super().nativeEvent(event_type,message)

        if msg.message == WM_NCCALCSIZE and msg.wParam:
            return True,0

        return super().nativeEvent(event_type,message)

    def sidebar(self):
        panel = QWidget()
        panel.setObjectName("sidebar")
        panel.setFixedWidth(SIDEBAR_WIDTH)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8,0,0)
        layout.setSpacing(18)
        layout.addWidget(self.nav,1)
        return panel

    def section_page(self,section_name):
        page = QWidget()
        page.setObjectName("page")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(20,25,70,30)
        page_layout.setSpacing(0)

        title = QLabel(section_name.title())
        title.setObjectName("pageTitle")
        page_layout.addWidget(title)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(28)
        form.setVerticalSpacing(18)

        section = getattr(self.config, section_name)
        for key,value in section.__dict__.items():
            label = QLabel(self.label_text(key))
            label.setObjectName("fieldLabel")
            form.addRow(label, self.editor_for(section_name,key,value))

        page_layout.addLayout(form)
        page_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.viewport().setStyleSheet("background-color: #ffffff;")
        scroll.setWidget(page)
        self.apply_default_scrollbar_style(scroll)
        return scroll

    def apply_default_scrollbar_style(self,scroll):
        for bar in (scroll.verticalScrollBar(),scroll.horizontalScrollBar()):
            bar.setStyleSheet(SCROLLBAR_STYLE)

    def editor_for(self, section, key, value):
        if isinstance(value, bool):
            editor = UwpToggle(value)
            editor.toggled.connect(lambda checked: self.set_value(section, key, checked))
            return editor

        if isinstance(value,int):
            editor = UwpSpinBox()
            editor.setRange(-100000, 100000)
            editor.setValue(value)
            editor.setFixedWidth(140)
            editor.valueChanged.connect(lambda number: self.set_value(section,key,number))
            return editor

        if isinstance(value, float):
            editor = UwpDoubleSpinBox()
            editor.setRange(-100000.0,100000.0)
            editor.setDecimals(3)
            editor.setValue(value)
            editor.setFixedWidth(140)
            editor.valueChanged.connect(lambda number: self.set_value(section,key,number))
            return editor

        if isinstance(value,(list,dict)):
            return self.json_editor(section,key,value)

        if key in OPTIONS:
            return self.combo_editor(section,key,value)

        if self.is_color(value):
            return self.color_editor(section,key,value)

        return self.text_editor(section,key,value)

    def combo_editor(self,section,key,value):
        editor = UwpComboBox()
        editor.addItems(OPTIONS[key])
        editor.setCurrentText(str(value))
        editor.setFixedWidth(280)
        editor.currentTextChanged.connect(lambda text: self.set_value(section, key, text))
        return editor

    def color_editor(self,section,key,value):
        editor = QLineEdit(value)
        editor.setFixedWidth(170)
        editor.editingFinished.connect(lambda: self.set_value(section, key, editor.text()))

        pick = UwpButton("Color")
        pick.clicked.connect(lambda: self.pick_color(section, key, editor))
        return self.row(editor, pick)

    def text_editor(self, section,key,value):
        editor = QLineEdit("" if value is None else str(value))
        editor.setMinimumWidth(260)
        editor.setMaximumWidth(420)
        editor.editingFinished.connect(lambda: self.set_value(section,key,self.text_value(section,key,editor)))

        if not self.is_path_field(key,value) or key.endswith("_format"):
            return editor

        browse = UwpButton("Browse")
        browse.clicked.connect(lambda: self.pick_file(section,key,editor))
        return self.row(editor, browse)

    def row(self, *widgets):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in widgets:
            layout.addWidget(widget)
        return row

    def json_editor(self, section, key, value):
        editor = QPlainTextEdit(json.dumps(value, indent=4))
        editor.setMinimumHeight(90)
        editor.setMinimumWidth(360)
        editor.setMaximumWidth(520)

        apply_button = UwpButton("Apply JSON")
        apply_button.clicked.connect(lambda: self.apply_json(section,key,editor))

        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(editor)
        layout.addWidget(apply_button)
        return box

    def apply_json(self, section, key, editor):
        try:
            self.set_value(section, key, json.loads(editor.toPlainText()))
        except json.JSONDecodeError as error:
            QMessageBox.warning(self, "Invalid JSON", f"{key} was not saved:\n{error}")

    def pick_file(self, section, key, editor):
        current = editor.text()
        start_dir = str(Path(current).parent) if current else str(Path.cwd())
        path, _ = QFileDialog.getOpenFileName(self, f"Select {key}", start_dir)

        if path:
            editor.setText(path.replace("\\", "/"))
            self.set_value(section, key, editor.text())

    def pick_color(self, section, key, editor):
        old_value = editor.text()
        color = QColorDialog.getColor(
            QColor(old_value),
            self,
            f"Select {key}",
            QColorDialog.ShowAlphaChannel,
        )

        if color.isValid():
            value = color.name(QColor.HexArgb if len(old_value) == 9 else QColor.HexRgb)
            editor.setText(value)
            self.set_value(section, key, value)

    def set_value(self, section, key, value):
        setattr(getattr(self.config, section), key, value)
        self.config.save(section)

    def text_value(self, section, key, editor):
        text = editor.text()
        return None if text == "" and (section, key) in self.nullable else text

    def find_nullable_fields(self):
        return {
            (section_name, key)
            for section_name in SECTIONS
            for key, value in getattr(self.config, section_name).__dict__.items()
            if value is None
        }

    def is_path_field(self, key, value):
        key = key.lower()
        return key == "path" or key.endswith("_icon") or key.endswith("_texture") or (
            isinstance(value, str) and ("/" in value or "\\" in value)
        )

    def is_color(self, value):
        return isinstance(value, str) and value.startswith("#") and len(value) in (7, 9)

    def label_text(self, key):
        return key.replace("_", " ").capitalize()

if __name__ == "__main__":
    app = QApplication([])
    gui = ConfigGui(Config())
    gui.show()
    app.exec()
