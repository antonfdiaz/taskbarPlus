from threading import Lock
from time import monotonic
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

config_change_callback = None
callback_lock = Lock()
last_config_event_at = 0.0
CONFIG_EVENT_DEBOUNCE_SECS = 0.2

def set_on_config_change(callback):
    global config_change_callback
    with callback_lock:
        config_change_callback = callback

def notify_config_change(path: str):
    global last_config_event_at

    callback = None
    now = monotonic()
    with callback_lock:
        if now-last_config_event_at < CONFIG_EVENT_DEBOUNCE_SECS:
            return

        last_config_event_at = now
        callback = config_change_callback

    if callback is not None:
        print(f"reloading config from {path}")
        callback()

class ConfigHandler(FileSystemEventHandler):
    def _is_config_file(self,path: str | None) -> bool:
        return bool(path) and path.endswith(".json")

    def on_modified(self,event):
        if not event.is_directory and self._is_config_file(event.src_path):
            notify_config_change(event.src_path)

    def on_created(self,event):
        if not event.is_directory and self._is_config_file(event.src_path):
            notify_config_change(event.src_path)

    def on_moved(self,event):
        if event.is_directory:
            return

        moved_path = getattr(event,"dest_path",None) or event.src_path
        if self._is_config_file(moved_path):
            notify_config_change(moved_path)

observer = Observer()
event_handler = ConfigHandler()

dir_to_watch = "config"
observer.schedule(event_handler,dir_to_watch,recursive=True)

def start():
    observer.start()
    print("observer started")
    try:
        observer.join()
    except (KeyboardInterrupt,SystemExit):
        print("stopping observer...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start()