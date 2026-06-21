from PySide6.QtGui import QIcon
from src.widgets import TaskbarBaseButton
import subprocess

class VolumeMixerButton(TaskbarBaseButton):
    """Button that opens the Windows volume mixer."""

    plugin_id = "volume_mixer"

    def __init__(self,config):
        super().__init__(config)
        self.apply_common_button_size()
        self.setToolTip("Open volume mixer")
        self.setIcon(QIcon(self.config.resolve_asset("assets/volume.png")))
        self.clicked.connect(self.open_volume_mixer)

    def open_volume_mixer(self):
        subprocess.Popen(["sndvol.exe"])
