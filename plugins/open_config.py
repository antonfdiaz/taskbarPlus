from PySide6.QtGui import QIcon
from src.widgets import TaskbarBaseButton
import subprocess

class OpenConfigButton(TaskbarBaseButton):
    """Button that opens the taskbarPlus config folder."""

    plugin_id = "open_config"

    def __init__(self,config):
        super().__init__(config)
        self.apply_common_button_size()
        self.setToolTip("Open config folder")
        self.setIcon(QIcon(self.config.resolve_asset("assets/setting.png")))
        self.clicked.connect(self.open_config)

    def open_config(self):
        subprocess.Popen(["explorer.exe",str(self.config.config_dir)])
