from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.config import Config
from src.models import TaskbarItem

class TaskbarAppsBar(QWidget):
    itemClicked = Signal(object,object)

    def __init__(self,items: list[TaskbarItem],config: Config):
        super().__init__()
        self.config = config
        self.items = items

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
            self.layout.addWidget(btn)

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
        current_time = QTime.currentTime().toString("hh:mm:ss")
        current_date = QDate.currentDate().toString("dd/MM/yyyy")
        self.setText(current_time+"\n"+current_date)
        QTimer.singleShot(1000,self.update_time)

class TaskbarButton(QAbstractButton):
    def __init__(self,item: TaskbarItem,config: Config,parent=None):
        super().__init__(parent)
        self.config = config
        self.item = item
        self.icon = item.icon
        self.hovered = False
        self.pressed = False

        self.setMouseTracking(True)
        self.setFixedSize(
            self.config.theme.button_width,
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

        bg = QColor(0,0,0,0)
        if self.pressed:
            bg = QColor(self.config.theme.active)
        elif self.hovered:
            bg = QColor(self.config.theme.hover)

        painter.fillRect(rect,bg)

        icon_size = self.config.theme.icon_size
        pix = self.icon.pixmap(icon_size,icon_size)

        x = (rect.width()-pix.width())//2
        y = (rect.height()-pix.height())//2
        painter.drawPixmap(x,y,pix)

        self.draw_indicator(painter,rect)

    def draw_indicator(self,painter: QPainter,rect: QRect):
        if not self.item.running:
            return
        
        indicator_h = 2
        indicator_y = rect.height()-indicator_h

        color = self.config.theme.accent
        #create darker color from accent (hex)
        darker_color = "#"+''.join([f"{max(0,int(int(self.config.theme.accent[i:i+2],16)*0.7)):02x}" for i in (1,3,5)])

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