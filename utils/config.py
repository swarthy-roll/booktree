import yaml
from enum import Enum

class Log_Level(Enum):
    CRITICAL = 'CRITICAL'
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    INFO = 'INFO'
    DEBUG = 'DEBUG'

class Config:
    config_file:str='config.yaml'
    file_types_to_process:list
    file_types:list
    source_directory:str
    target_directory:str
    create_opf_files:bool
    fetch_metadata_from:dict
    headless_mode:bool
    metadata_preference:list
    log_level:Log_Level

    def __init__(self):
        with open(self.config_file, "r") as file:
            data = yaml.safe_load(file)
        self.load_config(**data)

    def reload(self):
        with open(self.config_file, "r") as file:
            data = yaml.safe_load(file)
        self.__dict__.update(data)

    def __repr__(self):
        return (
            f"Config(\n"
            f"  file_types_to_process={self.file_types_to_process},\n"
            f"  file_types={self.file_types},\n"
            f"  source_directory='{self.source_directory}',\n"
            f"  target_directory='{self.target_directory}',\n"
            f"  create_opf_files={self.create_opf_files},\n"
            f"  fetch_metadata_from={self.fetch_metadata_from}\n"
            f"  headless_mode={self.headless_mode}\n"
            f"  log_level={self.log_level}\n"
            f")"
        )

    def load_config(self, 
                    file_types_to_process:dict, 
                    source_directory:str, 
                    target_directory:str, 
                    create_opf_files:bool, 
                    fetch_metadata_from:dict, 
                    headless_mode:bool, 
                    metadata_preference:list, 
                    log_level:str
                    ):
        # append the wildcards to each file type for proper extension identification
        self.file_types_to_process = [f"**/*.{item}" for item in file_types_to_process if file_types_to_process[item]] 
        self.file_types = [item for item in file_types_to_process if file_types_to_process[item]]
        self.source_directory = source_directory
        self.target_directory = target_directory
        self.create_opf_files = create_opf_files
        self.fetch_metadata_from = [item for item in fetch_metadata_from if fetch_metadata_from[item]]
        self.headless_mode = headless_mode
        self.metadata_preference = metadata_preference
        if not isinstance(Log_Level(log_level.upper()), Log_Level):
            raise ValueError(f'Invalid log level: {log_level}. Must be one of the following: CRITICAL, ERROR, WARNING, INFO, DEBUG.')
        self.log_level = Log_Level(log_level.upper())