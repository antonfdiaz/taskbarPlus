from PySide6.QtWidgets import *
from src.config import Config
from src.gui import MainWindow
from src.shell import show_taskbar,hide_taskbar
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    config = Config()

    hide_taskbar()

    window = MainWindow(config)
    window.show()
    window.closeEvent = lambda event: show_taskbar()
    
    sys.exit(app.exec())