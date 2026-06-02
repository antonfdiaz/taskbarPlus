from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigHandler(FileSystemEventHandler):
    def on_modified(self,event):
        if not event.is_directory and event.src_path.endswith(".json"):
            print(f"file {event.src_path} modified!")

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