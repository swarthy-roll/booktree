import yaml
from enum import Enum

class Level(Enum):
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10

class Config:
    config_file:str='config.yaml'
    file_types_to_process:list
    file_types:list
    source_directory:str
    target_directory:str
    create_opf_files:bool
    verbose:bool
    fetch_metadata_from:dict
    headless_mode:bool
    metadata_preference:list
    log_level:Level

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
            f"  verbose={self.verbose}\n"
            f"  fetch_metadata_from={self.fetch_metadata_from}\n"
            f"  headless_mode={self.headless_mode}\n"
            f")"
        )

    def load_config(self, file_types_to_process, source_directory, target_directory, create_opf_files, verbose, fetch_metadata_from, headless_mode, metadata_preference, log_level):
        # append the wildcards to each file type for proper extension identification
        self.file_types_to_process = [f"**/*.{item}" for item in file_types_to_process if file_types_to_process[item]] 
        self.file_types = [item for item in file_types_to_process if file_types_to_process[item]]
        self.source_directory = source_directory
        self.target_directory = target_directory
        self.create_opf_files = create_opf_files
        self.verbose = verbose
        self.fetch_metadata_from = [item for item in fetch_metadata_from if fetch_metadata_from[item]]
        self.headless_mode = headless_mode
        self.metadata_preference = metadata_preference
        self.log_level = log_level