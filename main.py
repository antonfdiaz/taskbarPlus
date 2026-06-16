from PySide6.QtWidgets import *
from PySide6.QtCore import QObject, Signal, Slot, QTimer, Qt
from src.config import Config
from src.gui import MainWindow
from src.shell import is_windows_7,get_real_winver,show_taskbar,hide_taskbar
import src.observer as observer
from threading import Thread
import sys
import threading
import traceback

class ErrorReporter(QObject):
    error_occurred = Signal(str,str)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.open_dialogs = []

    @Slot(str,str)
    def show_error(self,title: str,details: str):
        QTimer.singleShot(0,lambda: self._show_error(title,details))

    def _show_error(self,title: str,details: str):
        parent = QApplication.activeWindow()
        msgbox = QMessageBox(parent)
        msgbox.setIcon(QMessageBox.Critical)
        msgbox.setWindowTitle("taskbarPlus")
        msgbox.setText(title)
        msgbox.setDetailedText(details)
        msgbox.setAttribute(Qt.WA_DeleteOnClose,True)
        msgbox.finished.connect(lambda _result,dialog=msgbox: self.open_dialogs.remove(dialog) if dialog in self.open_dialogs else None)
        self.open_dialogs.append(msgbox)
        msgbox.open()

def install_error_dialogs():
    reporter = ErrorReporter(QApplication.instance())
    reporter.error_occurred.connect(reporter.show_error,Qt.QueuedConnection)

    old_excepthook = sys.excepthook
    old_threading_excepthook = threading.excepthook

    def show_exception(exc_type,exc_value,exc_traceback):
        if issubclass(exc_type,(KeyboardInterrupt,SystemExit)):
            old_excepthook(exc_type,exc_value,exc_traceback)
            return

        details = "".join(traceback.format_exception(exc_type,exc_value,exc_traceback))
        print(details)
        reporter.error_occurred.emit("An unexpected error occurred.\nClick 'Show Details...' for more information.",details)

    def show_thread_exception(args):
        if issubclass(args.exc_type,(KeyboardInterrupt,SystemExit)):
            old_threading_excepthook(args)
            return

        show_exception(args.exc_type,args.exc_value,args.exc_traceback)

    sys.excepthook = show_exception
    threading.excepthook = show_thread_exception
    return reporter

if __name__ == "__main__":
    app = QApplication(sys.argv)
    error_reporter = install_error_dialogs()

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
