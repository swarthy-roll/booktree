from dataclasses import dataclass, field
import os, subprocess, re, json, hashlib, traceback
from ebooklib import epub
from pypdf import PdfReader
from peewee import IntegrityError
from pathvalidate import sanitize_filename
from utils import utils
from utils.config import Config
from utils.goodreads import Goodreads
from entities.book import Book
from entities.logger import Logger
from entities.contributor import Contributor
import entities.series as Series, entities.contributor as Contributor
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
    probe_results:str = ""
    book:list[Book] = field(default_factory=list)
    config:Config = None
    exists_in_db:bool = False
    logger:Logger = None

    def __init__(self, full_path:str, config:Config):
        self.logger = Logger()
        self.config = config
        self.set_full_path(full_path)
        self.book = []

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

    def set_media_path(self):
        try:
            target_path:str = self.config.target_directory.get('base_directory')
            tokens = self.get_tokens_by_preference()

            if tokens.get('series', None):
                target_path += self.config.target_directory.get('in_series_format')
            else:
                target_path += self.config.target_directory.get('no_series_format')
            
            self.media_path = target_path.format(**tokens)
        except Exception:
            self.logger.log('ERROR',f'Error while attempting to set the media path for {self.full_path}. {traceback.format_exc()}')

    def get_tokens_by_preference(self):
        # result is a book object that is the result of all book objects coalesced into one based on the metadata preference
        tokens = {}
        self.sort_books_by_preference()

        # retrieve author
        author = utils.coalesce('authors', self.book)
        if author: 
            author = utils.get_first_item(author) # in case of multiple authors, get the first one
        if not author: author = Contributor('Unknown') 
        tokens["author"] = sanitize_filename(author.name)

        # retrieve series
        series_object = utils.coalesce('series', self.book)
        if series_object: 
            series = utils.get_first_item(series_object) # in case of multiple series, get the first one
            tokens["series"] = sanitize_filename(series.name)
            tokens["part"] = sanitize_filename(series.part)

        # retrieve title
        tokens["title"] = sanitize_filename(utils.coalesce('title', self.book))

        self.logger.log('DEBUG',f'Media path tokens for {self.full_path}: {tokens.__str__()}')

        return tokens

    def sort_books_by_preference(self):
        # result is a reordering of the book objects to align with the preferred metadata sources from the config file
        
        # creates a mapping between a book source and the preference
        order_mapping = {value: index for index, value in enumerate(self.config.get_metadata_preference())} 

        # sorts the existing book objects using the order mapping defined above
        self.book = sorted(self.book, key=lambda obj: order_mapping.get(obj.source, float('inf')))

    def create_fingerprint(self):
        chunk_size = 1024 * 1024 
        algorithm = 'sha256'
        hash_func = hashlib.new(algorithm)

        try:
            with open(self.full_path, 'rb') as f:
                chunk = f.read(chunk_size)
                hash_func.update(chunk)

            return hash_func.hexdigest()
        except Exception:
            self.logger.log('ERROR',f'Error while generating a fingerprint for {self.full_path}: {traceback.format_exc()}')
    
    def exists(self):
        if self.exists_in_db is None:
            self.exists_in_db = File_Model.record_exists('full_path',self.full_path)
        return self.exists_in_db

    def process(self):
        self.logger.log('INFO', f'Processing file {self.full_path}...')
        self.set_file_name()
        self.set_source_path()
        self.set_extension()
        self.set_fingerprint()
        self.probe_file()
        self.fetch_metadata()
        self.set_media_path()
        self.create_hardlink()

    def save(self):
        # a transaction here helps in two ways. firstly, if something errors out, we don't get a partial commit. 
        # secondly, a transaction prevents any race conditions. committing everything at once allows the db to commit items in the order needed
        with File_Model._meta.database.atomic() as transaction:
            try:
                file, created = File_Model.get_or_create(file_name=self.file_name,
                                                        full_path=self.full_path,
                                                        source_path=self.source_path,
                                                        extension=self.extension,
                                                        media_path=self.media_path,
                                                        fingerprint=self.fingerprint,
                                                        is_matched=self.is_matched,
                                                        is_hardlinked=self.is_hardlinked,
                                                        probe_results=self.probe_results
                                                        )
                if created:
                    for book in self.book: 
                        book = book.save()
                        Book_File_Model.get_or_create(book=book, file=file)
                    self.logger.log('INFO',f'File saved to the database successfully! File: {self.full_path}')
                return created
            except IntegrityError:
                self.logger.log('ERROR',f'Could not save File record: {self.__str__()}: {traceback.format_exc()}') 
                transaction.rollback()

    def move(self, destination):
        try:
            self.set_full_path(destination)
            self.set_source_path()
            
            File_Model.update(full_path=self.full_path, source_path=self.source_path)
        except IntegrityError:
            self.logger.log('ERROR',f'Could not update file after move: {self.__str__()}: {traceback.format_exc()}') 
    
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

    def fetch_metadata(self):
        for source in self.config.fetch_metadata_from:
            match source, self.extension:
                case "goodreads", 'epub' | 'pdf':
                    self.logger.log('INFO', f'Fetching metadata from Goodreads for {self.full_path}...')
                    goodreads = Goodreads(self.config)
                    book = goodreads.fetch_all(Book(source = 2), isbn=self.book[0].isbn, title=self.book[0].get_sanitized_title(), author=self.book[0].get_authors(' '))
                    if book: 
                        self.is_matched = True
                        self.book.append(book)
                case "audible", 'm4b':
                    print("audible")
                case "mam", 'epub':
                    print("mam")

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
                metadata = self._probe_pdf()
        try:
            if metadata:
                mapping = self._metadata_mapping()
                genres = metadata.get(mapping.get("genres"), None)
                tags = metadata.get(mapping.get("tags"), None)
                book = Book(source = 1)
                book.title = metadata.get(mapping.get("title"), self.file_name)
                book.subtitle = metadata.get(mapping.get("subtitle"), None)
                book.set_authors(metadata.get(mapping.get("authors"), None))
                book.publisher = metadata.get(mapping.get("publisher"), None)
                book.language = metadata.get(mapping.get("language"), None)
                book.description = metadata.get(mapping.get("description"), None)
                book.set_genres(metadata.get(mapping.get("genres"), None))
                book.set_tags(tags if tags is not None else genres) #by default, look for explicit tags, but fallback on genres (if they exist)
                book.publication_year = metadata.get(mapping.get("publication_year"), None)
                book.set_series(metadata.get(mapping.get("series"), None))
                book.set_isbn(metadata.get(mapping.get("isbn"), None))

                #print(book)
                self.book.append(book)
        except Exception:
            self.logger.log('ERROR',f'Could not create book object for {self.file_name} using probe metadata: {traceback.format_exc()}') 

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
                         "series": "calibre:series",
                         "isbn": "identifier"
                         }
                ,"pdf": {"title": "title",
                         "authors": "authors",
                         "genres": "genres",
                         "publisher": "publisher",
                         "isbn": "isbn",
                         "description": "description",
                         "language": "language",
                         "publication_year": "publication_year"
                         }
        }.get(self.extension)
    
    def _probe_pdf(self):
        try:
            genres:str = None 
            publisher:str = None
            language:str = None
            description:str = None
            publication_year:str = None
            isbn:str = None
            book = PdfReader(self.full_path)
            metadata = book.metadata
            
            # the pypdf lib doesn't expose these fields as accessible attributes, so we access them manually if they exist
            if book.xmp_metadata:
                genres = ''.join(book.xmp_metadata.dc_subject) if book.xmp_metadata.dc_subject else None
                publisher = book.xmp_metadata.dc_publisher[0] if book.xmp_metadata.dc_publisher else None
                language = book.xmp_metadata.dc_language[0] if book.xmp_metadata.dc_language else None
                description = book.xmp_metadata.dc_description['x-default'] if book.xmp_metadata.dc_description['x-default'] else None
                publication_year = book.xmp_metadata.dc_date[0].year if book.xmp_metadata.dc_date else None
                isbn = book.xmp_metadata.custom_properties.get('isbn', None)

            result = {
                "title": metadata.title,
                "authors": metadata.author,
                "genres": genres, # convert to a comma separated string
                "publisher": publisher,
                "isbn": isbn,
                "description": description,
                "language": language,
                "publication_year": publication_year
            }
            return result
        except Exception:
            self.logger.log('ERROR',f'Error occurred while probing pdf {self.full_path}: {traceback.format_exc()}')

    def _probe_epub(self):
        attributes = {'DC': ['identifier','title','subtitle','language','contributor','coverage','creator','date','description','format','publisher','relation','rights','source','subject','type','tag']
                    ,'OPF': ['calibre:series','calibre:series_index']}
        try:
            book = epub.read_epub(self.full_path)
            self.probe_results = book.metadata
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
            
        except Exception:
            self.logger.log('ERROR',f'An error occurred while probing {self.full_path}: {traceback.format_exc()}') 
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
        book=Book()
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

    def isCollection (bookFile, source_path):
        #we assume that most books are formatted this way /Book/Files.m4b
        #we assume that this is a collection, if the file is 3 levels deep, /Book/Another Book or CD/Files.m4b

        relPath = os.path.relpath(bookFile, source_path).split(os.sep)
        return (len(relPath) > 2)
    
    def create_hardlink(self):
        if not os.path.exists(self.media_path):
            self.logger.log('DEBUG',f'Created target directory: {self.media_path}...')
            os.makedirs(self.media_path, exist_ok=True)
        
        media_path = os.path.join(self.media_path, self.file_name)
        if (not os.path.exists(media_path)):
            try:
                os.link(self.full_path, media_path)
                self.is_hardlinked = True
                self.logger.log('INFO',f'Hardlink created for {self.full_path} at {self.media_path}.')
            except Exception as e:
                self.logger.log('ERROR', f'Error occurred while attempting to hardlink file {self.full_path}. {traceback.format_exc()}')
        else:
            self.logger.log('DEBUG', f'Skipped hardlink for: {self.full_path}. Hardlink already exists at {self.media_path}.')
        return self.is_hardlinked