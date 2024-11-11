import logging, datetime
from model.logger import Logger as Logger_Model

class Logger:
    def __init__(self, name="MessageLogger", log_to_console=True, log_to_db=False, log_level="INFO"):
        self.logger = logging.getLogger(name)
        self.set_log_level(log_level)  # Set initial log level

        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(self._get_formatter())
            self.logger.addHandler(console_handler)
        
        if log_to_db:
            db_handler = DatabaseLogHandler()
            db_handler.setFormatter(self._get_formatter())
            self.logger.addHandler(db_handler)

    def set_log_level(self, level):
        numeric_level = getattr(logging, level.upper(), logging.INFO)  # Default to INFO if invalid level
        self.logger.setLevel(numeric_level)
        for handler in self.logger.handlers:
            handler.setLevel(numeric_level)

    def _get_formatter(self):
        return logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def log(self, level, message):
        if level == "INFO":
            self.logger.info(message)
        elif level == "DEBUG":
            self.logger.debug(message)
        elif level == "WARNING":
            self.logger.warning(message)
        elif level == "ERROR":
            self.logger.error(message)
        elif level == "CRITICAL":
            self.logger.critical(message)

class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = Logger_Model(
            message=self.format(record),
            level=record.levelname,
            timestamp=datetime.datetime.fromtimestamp(record.created)
        )
        log_entry.save()  # Save the log entry to the database