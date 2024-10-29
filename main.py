#from database.table import create_tables, drop_all_tables
import database.table as Table
#import utils.file as file
import utils.scanner as Scanner
import utils.config as Config
import entities.file as File

def main():
    # timer begin
    # get all files
    config = Config.Config()
    print(config)

    #file = File.File(r"C:\Users\Aaron\Documents\Jeff VanderMeer - Authority.epub", config)
    #print(file)
    #for f in file.get_all_files(config.source_directory,config.file_types_to_process):
    #    print(f)

    #    file.probe_file(r"C:\Users\Aaron\Documents\\" + f)
    directory_scanner = Scanner.Scanner(scan_target=config.source_directory, file_types=config.file_types_to_process, config=config)
    directory_scanner.start()

    # iterate over every file

        #fingerprint the file

        # check db for match
        
            # probe the file to obtain metadata

            # attempt to match the book on goodreads/audible/mam
            
            # create a record in db for the file

            # create OPF file

            #append details to the log file

    #timer end

if __name__ == '__main__':
    # TODO: add logic to delete tables when in dev mode
    Table.drop_all_tables()
    Table.create_tables()

    main()

    