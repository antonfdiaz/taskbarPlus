from PySide6.QtGui import QPainter,QPen
from PySide6.QtWidgets import QWidget
from src.utils import theme_color

class SeparatorWidget(QWidget):
    """A small vertical separator."""

    plugin_id = "separator"

    def __init__(self,config):
        super().__init__()
        self.config = config
        self.setFixedSize(8,self.config.theme.button_height)

    def paintEvent(self,event):
        painter = QPainter(self)
        try:
            color = theme_color(self.config.theme.foreground)
            color.setAlphaF(0.35)
            painter.setPen(QPen(color,1))
            x = self.width()//2
            painter.drawLine(x,6,x,self.height()-6)
        finally:
            painter.end()
