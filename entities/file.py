from dataclasses import dataclass, field
import os, subprocess, re, json, hashlib
from ebooklib import epub
from peewee import IntegrityError
from pathvalidate import sanitize_filename
from utils import utils, config
import entities.book as Book, entities.series as Series, entities.contributor as Contributor
from model.file import File as File_Model
from model.book_file import Book_File as Book_File_Model

@dataclass
class File:
    file_name:str = ""
    full_path:str = ""
    source_path:str = ""
    extension:str = ""
    media_path:str = ""
    fingerprint:str = ""
    is_matched:bool = False
    is_hardlinked:bool = False
    book:list[Book.Book] = field(default_factory=list)

    def __init__(self, full_path:str, config:config.Config):
        self.book = []
        self.set_full_path(full_path)
        self.set_file_name()
        self.set_source_path()
        self.set_extension()
        self.set_fingerprint()
        self.probe_file()

    def __str__(self):
        return (
                f"file:          {self.file_name}\n"
                f"full path:     {self.full_path}\n"
                f"source path:   {self.source_path}\n"
                f"extension:     {self.extension}\n"
                f"media path:    {self.media_path}\n"
                f"figerprint:    {self.fingerprint}\n"
                f"is matched:    {self.is_matched}\n"
                f"is hardlinked: {self.is_hardlinked}\n"
                f"book(s):       {[f'{item.title}' for item in getattr(self, 'book', [])] or 'None'}\n"
            )
    
    def set_file_name(self):
        self.file_name = self.parse_file_name()

    def set_full_path(self, full_path:str):
        self.full_path = full_path
    
    def set_source_path(self):
        self.source_path = os.path.dirname(self.full_path)

    def set_extension(self):
        self.extension = self.parse_extension()
    
    def set_fingerprint(self):
        self.fingerprint = self.create_fingerprint()

    def create_fingerprint(self):
        chunk_size = 1024 * 1024 
        algorithm = 'sha256'
        hash_func = hashlib.new(algorithm)

        try:
            with open(self.full_path, 'rb') as f:
                chunk = f.read(chunk_size)
                hash_func.update(chunk)

            return hash_func.hexdigest()
        except Exception as e:
            print(f"Error while generating a fingerprint for {self.full_path}: {e}")

    def save(self):
        with File_Model._meta.database.atomic() as transaction:
            try:
                file, created = File_Model.get_or_create(file_name=self.file_name,
                                                        full_path=self.full_path,
                                                        source_path=self.source_path,
                                                        extension=self.extension,
                                                        media_path=self.media_path,
                                                        fingerprint=self.fingerprint,
                                                        is_matched=self.is_matched,
                                                        is_hardlinked=self.is_hardlinked)
                if created:
                    for book in self.book: 
                        book = book.save()
                        Book_File_Model.get_or_create(book=book, file=file)
            except IntegrityError as e:
                print(f"ERROR: could not save file record: {self.__str__()}: {e}") 
                transaction.rollback()

    def move(self, destination):
        try:
            self.set_full_path(destination)
            self.set_source_path()
            
            File_Model.update(full_path=self.full_path, source_path=self.source_path)
        except IntegrityError as e:
            print(f"ERROR: could not update file after move: {self.__str__()}: {e}")
    
    def parse_extension(self):
        return os.path.splitext(self.file_name)[1].replace(".","")

    def hasNoParentFolder(self):
        return (len(self.getParentFolder())==0)
    
    def getParentFolder(file, source):
        #We normally assume that the file is in a folder, but some files are NOT in a subfolder
        parent=os.path.dirname(file)
        #check if the parent folder matches the source folder
        if (parent == source):
            #this file is bad and has no parent folder, use the filename as the parent folder
            return os.path.basename(file)
        else:
            return (parent.split(os.sep)[-1])

    def parse_file_name(self):
        return os.path.basename(self.full_path)

    def __probe_file__ (self):
        cmnd = ['ffprobe','-loglevel','error','-show_entries','format_tags:format=duration', '-of', 'default=noprint_wrappers=1:nokey=0', '-print_format', 'json', self.full_path]
        p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err =  p.communicate()
        return json.loads(out)

    def probe_file(self):

        match self.extension:
            case "epub":
                metadata = self._probe_epub()
            case "pdf":
                metadata = None
        try:
            if metadata:
                mapping = self._metadata_mapping()
                genres = metadata.get(mapping.get("genres"), None)
                tags = metadata.get(mapping.get("tags"), None)
                book = Book.Book(source=1)
                book.title = metadata.get(mapping.get("title"), None)
                book.subtitle = metadata.get(mapping.get("subtitle"), None)
                book.set_authors(metadata.get(mapping.get("authors"), None))
                book.publisher = metadata.get(mapping.get("publisher"), None)
                book.language = metadata.get(mapping.get("language"), None)
                book.description = metadata.get(mapping.get("description"), None)
                book.set_genres(metadata.get(mapping.get("genres"), None))
                book.set_tags(tags if tags is not None else genres) #by default, look for explicit tags, but fallback on genres (if they exist)
                book.publication_year = metadata.get(mapping.get("publication_year"), None)
                book.set_series(metadata.get(mapping.get("series"), None))

                print(book)
                self.book.append(book)
        except Exception as e:
            print(f"ERROR: could not create book object for {self.file_name}: {e}")

    def _metadata_mapping(self):
        return {
                "epub": {"title": "title",
                         "subtitle": "subtitle",
                         "authors": "creator",
                         "publisher": "publisher",
                         "language": "language",
                         "description": "description",
                         "genres": "subject",
                         "tags": "tag",
                         "publication_year": "date",
                         "series": "calibre:series"
                         }
                ,"pdf": {"title": "title", "subtitle": "subtitle"}
        }.get(self.extension)

    def _probe_epub(self):
        attributes = {'DC': ['identifier','title','subtitle','language','contributor','coverage','creator','date','description','format','publisher','relation','rights','source','subject','type','tag']
                    ,'OPF': ['calibre:series','calibre:series_index']}
        try:
            book = epub.read_epub(self.full_path)
            result = {}

            for namespace, fields in attributes.items():
                for field in fields:
                    metadata = book.get_metadata(namespace, field)
                    if metadata:
                        field_values = ','.join([v[0] for v in metadata if v[0]])
                        result[field] = field_values
                    else:
                        result[field] = None

            return result
            
        except Exception as e:
            print(f"ERROR while probing the epub {self.full_path}: {e}")
            return None

    def ffprobe(self):
        #ffprobe the file
        duration=0
        try:
            r = self.__probe_file__()
            duration = float(r["format"]["duration"])
            metadata= r["format"]["tags"]
        except Exception as e:
            metadata=dict()

        #parse and create a book object
        book=Book.Book()
        if 'AUDIBLE_ASIN' in metadata: book.asin=metadata["AUDIBLE_ASIN"]
        if 'title' in metadata: book.title=metadata["title"]
        if 'subtitle' in metadata: book.subtitle=metadata["subtitle"]
        #series and part, if provided
        if (('SERIES' in metadata) and ('PART' in metadata)): 
            book.series.append(Series.Series(metadata["SERIES"],metadata["PART"]))
        #parse album, assume it's a series
        if 'album' in metadata: book.series.append(Series.Series(metadata["album"],""))
        #parse authors
        if 'artist' in metadata: 
            #remove everything in parentheses firstm before parsing
            artist = re.sub(r"\(.+\)", "", metadata["artist"], flags=re.IGNORECASE)
            for author in artist.split(","):
                book.authors.append(Contributor.Contributor(utils.removeGA(author)))
        #parse narrators
        if 'composer' in metadata: 
            composer = re.sub(r"\(.+\)", "", metadata["composer"], flags=re.IGNORECASE)
            for narrator in composer.split(","):
                book.narrators.append(Contributor.Contributor(narrator))
        #duration in minutes
        book.duration = duration
        
        #return a book object created from  ffprobe
        self.ffprobeBook=book

        return book
    
    def hardlink_file(self):

        #check if the target path exists
        if (not os.path.exists(self.media_path)):
            #make dir path
            print (f"\tCreating target directory: {self.media_path} ")
            os.makedirs(self.media_path, exist_ok=True)
        
        #check if the file already exists in the target directory
        filename=os.path.join(self.media_path, self.file_name)
        if (not os.path.exists(filename)):
            try:
                os.link(self.source_path, filename)
                self.is_hardlinked = True
            except Exception as e:
                print (f"\tHardlink failed due to {e}")
        else:
            print (f"\tSkipped : {filename} exists")
                
        return self.isHardlinked
    
    def getConfigTargetPath(self, cfg, book):
        #Config
        in_series = cfg.get("Config/target_path/in_series")
        no_series = cfg.get("Config/target_path/no_series")
        disc_folder = cfg.get("Config/target_path/disc_folder")


        if (book is not None):
            #Get primary author
            if ((book.authors is not None) and (len(book.authors) == 0)):
                author="Unknown"
            else:
                author=book.authors[0].name  

            #standardize author name (replace . with space, and then make sure that there's only single space)
            author=utils.cleanseAuthor(author)

            #Get primary narrator
            if ((book.narrators is not None) and (len(book.authors) == 0)):
                narrators=""
            else:
                narrators=book.getNarrators()

            #is this a MultiCd file?
            disc = self.getParentFolder()
            if (not utils.isMultiCD(disc)):
                disc = ""

            #Does this book belong in a series - only take the first series?
            series=""
            part=""
            if (len(book.series) > 0):
                series = f"{utils.cleanseSeries(book.series[0].name)}"
                part = str(book.series[0].part)

            title = f"{utils.cleanseTitle(book.title)}"

            tokens = {}
            tokens["author"] = sanitize_filename(author)
            tokens["series"] = sanitize_filename(series)
            tokens["part"] = sanitize_filename(part)
            tokens["title"] = sanitize_filename(book.title)
            tokens["cleanTitle"] = sanitize_filename(title)
            tokens["disc"] = sanitize_filename(disc)
            tokens["narrators"] = f"{{{sanitize_filename(narrators)}}}"

            sPath = ""
            if len(book.series):
                x = in_series.format (**tokens)
                #use in_series format
                for p in x.split ("/"):
                    sPath=os.path.join (sPath, p)
            else:
                y = no_series.format (**tokens)
                #use no_series format
                for p in y.split ("/"):
                    sPath=os.path.join (sPath, p)

            #add disc for multidisc
            if len(disc):
                z = disc_folder.format (**tokens)
                sPath=os.path.join(sPath, z)

            return os.path.join(self.media_path, sPath)  
    
    def getTargetPaths(self, book, cfg):
        return self.getConfigTargetPath(cfg, book)
    
    def getLogRecord(self, bookMatch:Book.Book, cfg):
        #returns a dictionary of the record that gets logged
        book={
            "file":self.full_path,
            "isMatched": self.is_matched,
            "isHardLinked": self.is_hardlinked,
        }

        book=bookMatch.getDictionary(book)

        if cfg.get("Config/metadata") != "log":
            book["paths"]=self.getConfigTargetPath(cfg, bookMatch)

        return book
    

    def isCollection (bookFile, source_path):
        #we assume that most books are formatted this way /Book/Files.m4b
        #we assume that this is a collection, if the file is 3 levels deep, /Book/Another Book or CD/Files.m4b

        relPath = os.path.relpath(bookFile, source_path).split(os.sep)
        return (len(relPath) > 2)
    
    def createHardLinks(bookFiles, targetFolder="", dryRun=False):
        #hard link all the books in the list
        for f in bookFiles:
            #use Audible metadata or ID3 metadata
            if f.isMatched:
                book=f.audibleMatch
            else:
                book=f.ffprobeBook

            #if there is a book
            if (book is not None):
                #if a book belongs to multiple series, hardlink them to tall series
                for p in f.getTargetPaths(book):
                    prefix=""
                    if (not dryRun):
                        f.hardlinkFile(f.sourcePath, os.path.join(targetFolder, p))
                    else:
                        prefix = "[Dry Run] : "
                    print (f"{prefix}Hardlinking {f.sourcePath} to {os.path.join(targetFolder,p)}")
                print("\n", 40 * "-", "\n")