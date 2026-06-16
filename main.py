from PySide6.QtWidgets import *
from src.config import Config
from src.gui import MainWindow
from src.shell import is_windows_7,get_real_winver,show_taskbar,hide_taskbar
import src.observer as observer
from threading import Thread
import platform
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    config = Config()

    window = MainWindow(config)
    observer.set_on_config_change(window.config_reload_requested.emit)
    window.show()
    window.closeEvent = lambda event: show_taskbar()

    hide_taskbar()

    major,minor,build = get_real_winver()
    print(f"running on nt {major}.{minor}.{build}")
    
    if is_windows_7():
        #on w7 the start btn needs to be hidden individually
        from src.shell import hide_start_btn,show_start_btn
        hide_start_btn()
        window.closeEvent = lambda event: (show_taskbar(),show_start_btn())

    observer_thread = Thread(target=observer.start,args=(config.config_dir,),daemon=True)
    observer_thread.start()
    
    sys.exit(app.exec())