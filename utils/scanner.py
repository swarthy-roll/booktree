import os, time, threading
import utils.file as File_Utils
from entities.file import File
from utils.config import Config
from queue import Queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Scanner:
    file_queue:Queue
    scan_target:str
    file_types:list
    config:Config

    def __init__(self, scan_target, file_types, config):
        self.file_queue = Queue()
        self.scan_target = scan_target
        self.file_types = file_types
        self.config = config

    class NewFileHandler(FileSystemEventHandler):
        def __init__(self, file_queue):
            super().__init__()
            self.file_queue = file_queue

        def dispatch(self, event):
            print(f"Dispatched event type: {event.event_type}, Path: {event.src_path}")
            super().dispatch(event)

        def on_created(self, event):
            config = Config()
            extension = os.path.splitext(event.src_path)[1].replace(".","")

            if not event.is_directory and extension in config.file_types:
                print("past the if")
                time.sleep(.01) #wait for the file to be released by the system. copy/paste files creates a "file locked" issue which generates a permission denied error when reading the file briefly after creation
                self.file_queue.put(event.src_path)
                print(f"New file detected: {event.src_path}. Queue size now approx: {self.file_queue.qsize()}")

    def start(self):
        # use separate threads for file processing, initial directory scan, and directory monitoring
        threading.Thread(target=self.process_files, daemon=True).start()
        threading.Thread(target=self.scan_existing_files).start()
        self.monitor_directory()

    def process_files(self):
        while True:
            file_path = self.file_queue.get()  
            try:
                print(f"Processing file: {file_path}")
                file = File(full_path=file_path, config=self.config)
                file.save()
                
                file = None
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
            finally:
                self.file_queue.task_done()
                print(f"File processing complete. Queue size approx: {self.file_queue.qsize()}")

    def scan_existing_files(self):
        print("Starting initial scan...")
        for file in File_Utils.get_all_files(self.scan_target, self.file_types):
            file_path = os.path.join(self.scan_target, file)
            print(f"Found existing file: {file_path}")
            self.file_queue.put(file_path)
        print("Initial scan complete.")

    def monitor_directory(self):
        print(f"Monitoring directory: {self.scan_target}")
        
        event_handler = self.NewFileHandler(self.file_queue)
        observer = Observer()
        observer.schedule(event_handler, path=self.scan_target, recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping directory watcher.")
            observer.stop()

        observer.join()