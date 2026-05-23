from PySide6.QtWidgets import *
from src.config import Config
from src.gui import MainWindow
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    config = Config()

    window = MainWindow(config)
    window.show()
    
    sys.exit(app.exec())