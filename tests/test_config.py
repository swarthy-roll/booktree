from utils.config import Config, Log_Level

def test_config_instantiation():
    config = Config()
    assert config is not None

def test_config_load_not_none():
    config = Config()
    assert config.file_types_to_process is not None
    assert config.file_types is not None
    assert config.source_directory is not None
    assert config.target_directory is not None
    assert config.create_opf_files is not None
    assert config.fetch_metadata_from is not None
    assert config.headless_mode is not None
    assert config.metadata_preference is not None
    assert config.log_level is not None
    assert config.force_reprocess is not None

def test_config_load_types():
    config = Config()
    assert isinstance(config.file_types_to_process, list) == True
    assert isinstance(config.file_types, list) == True
    assert isinstance(config.source_directory, str) == True
    assert isinstance(config.target_directory, dict) == True
    assert isinstance(config.create_opf_files, bool) == True
    assert isinstance(config.fetch_metadata_from, list) == True
    assert isinstance(config.headless_mode, bool) == True
    assert isinstance(config.metadata_preference, list) == True
    assert isinstance(config.log_level, Log_Level) == True
    assert isinstance(config.force_reprocess, bool) == True