import database.table as Table
import utils.scanner as Scanner
import utils.config as Config
from entities.logger import Logger

def main():
    # start scanner
    directory_scanner = Scanner.Scanner(scan_target=config.source_directory, file_types=config.file_types_to_process, config=config, logger=logger)
    directory_scanner.start()

if __name__ == '__main__':
    config = Config.Config()
    if config.force_reprocess:
        Table.drop_all_tables()
    Table.create_tables()
    
    logger = Logger()
    logger.log('DEBUG','Starting app...')
    logger.log('DEBUG',f'Config: {config}')

    main()

    