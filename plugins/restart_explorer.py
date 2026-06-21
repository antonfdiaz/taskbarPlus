from src.widgets import TaskbarBaseButton
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMessageBox
from src.shell import hide_taskbar
import time
import subprocess

class RestartExplorerButton(TaskbarBaseButton):
    """Button that restarts Windows Explorer."""

    plugin_id = "restart_explorer"

    def __init__(self,config):
        super().__init__(config)
        self.setFixedSize(self.common_button_width(),self.common_button_height())
        self.setToolTip("Restart Explorer")
        self.clicked.connect(self.restart_explorer)
        self.setIcon(QIcon(self.config.resolve_asset("assets/refresh.png")))

    def restart_explorer(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Restart Explorer")
        msg.setText("Are you sure you want to restart Windows Explorer?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        result = msg.exec()
        if result == QMessageBox.Yes:
            subprocess.run("taskkill /f /im explorer.exe && start explorer.exe",shell=True)
            time.sleep(1)
            hide_taskbar()