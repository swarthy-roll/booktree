import logging, datetime, sys
from model.logger import Logger as Logger_Model
from utils.config import Config

class Logger:
    config:Config
    _logger = None  
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._logger:
            cls._logger = logging.getLogger("MessageLogger")
            cls._instance = super(Logger, cls).__new__(cls)
            cls._setup_logger(cls._logger, *args, **kwargs)
        return cls._instance
    
    @staticmethod
    def _setup_logger(logger):
        # configure console logging
        console_handler = logging.StreamHandler()
        logger.addHandler(console_handler)
    
        # configure database logging
        db_handler = DatabaseLogHandler()
        logger.addHandler(db_handler)

        # catch all "print" or error messages and redirect them to this logger class
        sys.stdout = StreamToLogger(logger, logging.DEBUG)
        sys.stderr = StreamToLogger(logger, logging.ERROR)

    def __init__(self, log_level=None):
        self.config = Config()
        if not log_level:
            self.set_log_level(self.config.log_level.name)  # set log level as defined in the config

        self._set_formatter() # update all the handlers with custom message formatting

    def set_log_level(self, level):
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        self._logger.setLevel(numeric_level)
        for handler in self._logger.handlers:
            handler.setLevel(numeric_level)

    def _get_formatter(self):
        return logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def _set_formatter(self):
        for handler in self._logger.handlers:
            handler.setFormatter(self._get_formatter())
    
    def log(self, level, message):
        if level == "INFO":
            self._logger.info(message)
        elif level == "DEBUG":
            self._logger.debug(message)
        elif level == "WARNING":
            self._logger.warning(message)
        elif level == "ERROR":
            self._logger.error(message)
        elif level == "CRITICAL":
            self._logger.critical(message)

class StreamToLogger:
    # redirects stdout or stderr to a logger instance.
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level

    def write(self, message):
        if message.strip():  # avoid logging empty lines
            self.logger.log(self.log_level, message.strip())

    def flush(self):
        pass  # no flush needed for logging

class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = Logger_Model(
            message=self.format(record),
            level=record.levelname,
            name=record.name,
            timestamp=datetime.datetime.fromtimestamp(record.created)
        )
        log_entry.save()  # Save the log entry to the database