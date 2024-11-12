import os, time, threading
import utils.file as File_Utils
from entities.file import File
from entities.logger import Logger
from utils.config import Config
from queue import Queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Scanner:
    file_queue:Queue
    scan_target:str
    file_types:list
    config:Config
    logger:Logger

    def __init__(self, scan_target, file_types, config:Config, logger:Logger):
        self.file_queue = Queue()
        self.scan_target = scan_target
        self.file_types = file_types
        self.config = config
        self.logger = logger
        self.logger.log('DEBUG', f'Initialized Scanner class. Scanning for file types {self.file_types} in directory {self.scan_target}.')

    class NewFileHandler(FileSystemEventHandler):
        def __init__(self, file_queue, logger):
            super().__init__()
            self.file_queue = file_queue
            self.logger = logger

        def dispatch(self, event):
            self.logger.log('DEBUG', f'Dispatched event type: {event.event_type}, Path: {event.src_path}')
            #Scanner.logger.log('DEBUG', f'Dispatched event type: {event.event_type}, Path: {event.src_path}')
            super().dispatch(event)

        def on_created(self, event):
            config = Config()
            extension = os.path.splitext(event.src_path)[1].replace(".","")

            if not event.is_directory and extension in config.file_types:
                time.sleep(.01) #wait for the file to be released by the system. copy/paste files creates a "file locked" issue which generates a permission denied error when reading the file briefly after creation
                self.file_queue.put(event.src_path)
                self.logger.log('INFO', f'New file detected: {event.src_path}. Queue size now approx: {self.file_queue.qsize()}')

    def start(self):
        # use separate threads for file processing, initial directory scan, and directory monitoring
        threading.Thread(target=self.process_files, daemon=True, name='FileProcessingThread').start()
        threading.Thread(target=self.scan_existing_files, name='InitialDirectoryScanThread').start()
        self.monitor_directory()

    def process_files(self):
        while True:
            file_path = self.file_queue.get()  
            try:
                self.logger.log('INFO', f'Queuing file for processing: {file_path}...')
                file = File(full_path=file_path, config=self.config)
                if file.exists_in_db:
                    self.logger.log('INFO',f'Skipping file: {file_path} since it has already been processed.')
                else:
                    file.save()

                file = None
            except Exception as e:
                self.logger.log('WARNING', f'Error processing {file_path}: {e}.')
            finally:
                self.file_queue.task_done()
                self.logger.log('INFO', f'File processing completed for {file_path}.')
                self.logger.log('INFO', f'Queue size approximately: {self.file_queue.qsize()}.')

    def scan_existing_files(self):
        self.logger.log('INFO', f'Starting initial scan of {self.scan_target}...')
        for file in File_Utils.get_all_files(self.scan_target, self.file_types):
            file_path = os.path.join(self.scan_target, file)
            self.logger.log('INFO', f'Found existing file: {file_path}. Adding to queue...')
            self.file_queue.put(file_path)
        self.logger.log('INFO', f'Initial scan complete!')

    def monitor_directory(self):
        self.logger.log('INFO', f'Monitoring thread started for directory: {self.scan_target}...')
        
        event_handler = self.NewFileHandler(self.file_queue, self.logger)
        observer = Observer()
        observer.schedule(event_handler, path=self.scan_target, recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.log('INFO', f'User interrupted. Stopping directory watcher.')
            observer.stop()

        observer.join()