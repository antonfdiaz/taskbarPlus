from PySide6.QtWidgets import *
from src.config import Config
from src.gui import MainWindow
from src.shell import show_taskbar,hide_taskbar
import src.observer as observer
from threading import Thread
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    config = Config()

    window = MainWindow(config)
    observer.set_on_config_change(window.config_reload_requested.emit)
    window.show()
    window.closeEvent = lambda event: show_taskbar()

    hide_taskbar()

    observer_thread = Thread(target=observer.start,args=(config.config_dir,),daemon=True)
    observer_thread.start()
    
    sys.exit(app.exec())