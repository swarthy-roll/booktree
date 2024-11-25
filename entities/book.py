from dataclasses import dataclass, field
from peewee import IntegrityError
from glob import iglob
from enum import Enum
from utils import utils
from model.book import Book as Book_Model
from model.book_author import Book_Author as Book_Author_Model
from model.book_genres import Book_Genres as Book_Genres_Model
from model.book_narrator import Book_Narrator as Book_Narrator_Model
from model.book_series import Book_Series as Book_Series_Model
from model.book_tags import Book_Tags as Book_Tags_Model
from entities.series import Series as Series_Entity
from entities.contributor import Contributor as Contributor_Entity
from entities.category import Categories as Category_Entity
from entities.genre import Genre as Genre_Entity
import os, re

class Source(Enum):
    NONE = 0
    EMBEDDED = 1
    GOODREADS = 2
    AUDIBLE = 3
    MAM = 4
    
@dataclass
class Book:
    asin:str=""
    isbn:str=""
    title:str=""
    subtitle:str=""
    publication_year:str=""
    publisher:str=""
    length:int=0
    duration:float=0
    match_rate:int=0
    language:str="en"
    snatched:bool=False
    description:str=""
    raw_source:str=""
    series:list[Series_Entity]= field(default_factory=list)
    authors:list[Contributor_Entity]= field(default_factory=list)
    narrators:list[Contributor_Entity]= field(default_factory=list)
    genres:list[Category_Entity]= field(default_factory=list)
    tags:list[Category_Entity]= field(default_factory=list)
    files:list[str]= field(default_factory=list)
    book_cover_url:str=""
    source:Source=0

    def __init__(self, source:Source):
        self.source = source
        self.series = []
        self.authors = []
        self.narrators = []
        self.genres = []
        self.tags = []

    def __str__(self):
        return (
                f"title:             {self.title}\n"
                f"subtitle:          {self.subtitle}\n"
                f"authors:           {self.authors}\n"
                f"language:          {self.language}\n"
                f"publication year:  {self.publication_year}\n"
                f"publisher:         {self.publisher}\n"
                f"description:       {self.description}\n"
                f"series:            {self.series}\n"
                f"genres:            {self.genres}\n"
                f"tags:              {self.tags}\n"
                f"isbn:              {self.isbn}\n"
                f"book cover url:    {self.book_cover_url}\n"
                f"source:            {self.source}\n"
            )

    def addFiles(self, file):
        self.files.append(file)
    
    def getCleanTitle(self):
        #remove author
        title = self.title
        for author in self.authors:
            title = re.sub (f"{re.escape(author.name)}", "", title, flags=re.IGNORECASE)

        #Remove the rest
        title = utils.cleanseTitle(title, True, True)
        
        return title
    
    def get_authors(self, delimiter=",", cleanse=False):
        # returns a delimited list of authors
        if len(self.authors):
            if cleanse:
                return delimiter.join(self.sanitize_authors())
            else:
                authors = []
                for author in self.authors:
                    authors.append(author.name)
                return delimiter.join(authors)
        else:
            return ""
    
    def get_series(self, delimiter=",", encloser="", stripaccents=True):
        if len(self.series):
            return self.getList(self.series, delimiter, encloser, stripaccents=True)
        else:
            return ""
    
    def get_narrators(self, delimiter=",", encloser="", stripaccents=True):
        if len(self.narrators):
            return self.getList(self.narrators, delimiter, encloser, stripaccents=True) 
        else:
            return ""
        
    def get_genres(self, delimiter=",", encloser="", stripaccents=True):
        if len(self.genres):
            return self.getList(self.genres, delimiter, encloser, stripaccents=True) 
        else:
            return ""

    def get_tags(self, delimiter=",", encloser="", stripaccents=True):
        if len(self.tags):
            return self.getList(self.tags, delimiter, encloser, stripaccents=True) 
        else:
            return ""
    
    def get_series_parts(self, delimiter=",", encloser="", stripaccents=True):
        seriesparts = []
        for s in self.series:
            if len(s.name.strip()):
                seriesparts.append(Series_Entity(f"{s.name} {s.separator}{s.part}")) 
            
        return self.getList(seriesparts, delimiter, encloser, stripaccents=True) 
    
    def set_title(self, title_text: str):
        if title_text:
            # sometimes, the title text will contain the subtitle, delimited by a semicolon. this parses the text into three parts and sets the title/subtitle accordingly
            title, _, subtitle = title_text.partition(":")
            self.title = title.strip()
            self.set_subtitle(subtitle.strip() if subtitle else None)

    def set_subtitle(self, subtitle):
        self.subtitle = subtitle

    def set_authors(self, authors:str):
        #Given a csv of authors, convert it to a list
        if len(authors.strip()):
            for author in authors.split (","):
                self.authors.append(Contributor_Entity(author))

    def set_narrators(self, narrators):
        #Given a csv of narrators, convert it to a list
        if len(narrators.strip()):
            for narrator in narrators.split (","):
                self.narrators.append(Contributor_Entity(narrator))

    def set_genres(self, genres:str, limit=2):
        #Given a csv of genres, convert it to a list. Default is two, fiction/nonfiction use one of the default spots
        if genres:
            genre_entity = Genre_Entity()
            genre_list = []

            for genre in genres.split(','):
                genre_list.append(utils.to_camel_case(genre.strip()))

            if len(genres):
                if any(genre for genre in genre_list if genre in genre_entity.fiction):
                    self.genres.append(Category_Entity("Fiction"))
                elif any(genre for genre in genres.split(",") if genre in genre_entity.nonfiction):
                    self.genres.append(Category_Entity("Nonfiction"))
                else: 
                    self.genres.append(Category_Entity("Unknown"))

                for genre in [genre for genre in genre_list if genre not in genre_entity.top_level_genres][:limit-1]:
                    self.genres.append(Category_Entity(genre))

    def set_tags(self, tags:str):
        #Given a csv of tags, convert it to a list
        if tags:
            genre_entity = Genre_Entity()
            tag_list = []

            for tag in tags.split(','):
                tag_list.append(utils.to_camel_case(tag.strip()))

            for tag in [tag for tag in tag_list if tag not in genre_entity.top_level_genres]:
                self.tags.append(Category_Entity(tag))

    def set_series(self, series:str):
        #Given a csv of series, convert it to a list
        if series:
            if len(series.strip()):
                for s in list([series]):
                    p = s.split("#")
                    #print (f"Series: {s}\nSplit: {p}")
                    if len(p) > 1: 
                        self.series.append(Series_Entity(str(p[0]).strip(), str(p[1]).strip()))
                    else:
                        self.series.append(Series_Entity(str(p[0]).strip(), ""))
    
    def set_isbn(self, identifier:str):
        # expects either a single isbn or a csv of identifiers that might have an isbn
        if identifier:
            pattern = r'^9\d{12}$'
            items = identifier.split(',')
            self.isbn = next((item for item in items if re.match(pattern, item)), None)

    def save(self):
        with Book_Model._meta.database.atomic() as transaction:
            try:
                book, result = Book_Model.get_or_create(asin=self.asin,
                                                        isbn=self.isbn,
                                                        title=self.title,
                                                        subtitle=self.subtitle,
                                                        publication_year=self.publication_year,
                                                        publisher=self.publisher,
                                                        length=self.length,
                                                        duration=self.duration,
                                                        match_rate=self.match_rate,
                                                        language=self.language,
                                                        snatched=self.snatched,
                                                        description=self.description,
                                                        raw_source=self.raw_source,
                                                        book_cover_url=self.book_cover_url,
                                                        source=self.source)
                
                for author in self.authors:
                    author = author.save()

                    Book_Author_Model.get_or_create(book=book, author=author)

                for narrator in self.narrators:
                    narrator = narrator.save()

                    Book_Narrator_Model.get_or_create(book=book, narrator=narrator)
                
                for genre in self.genres:
                    genre = genre.save()

                    Book_Genres_Model.get_or_create(book=book, genres=genre)
                
                for tag in self.tags:
                    tag = tag.save()

                    Book_Tags_Model.get_or_create(book=book, tags=tag)
                
                for series in self.series:
                    series = series.save()

                    Book_Series_Model.get_or_create(book=book, series=series)
                
                return book

            except IntegrityError as e:
                print(f"ERROR: could not save book record: {self.__str__()}: {e}") 
                transaction.rollback()
    
    def createOPF(self, path):
        try:
            # --- Generate .opf Metadata file ---
            opfTemplate=os.path.join(os.getcwd(), "templates/booktemplate.opf") 
            with open(opfTemplate, mode='r') as file:
                template = file.read()

            # - Author -
            authors=""
            for author in self.authors:
                authors += f"\t<dc:creator opf:role='aut'>{author.name.replace("&", "&amp;")}</dc:creator>\n"
            template = re.sub(r"__AUTHORS__", authors, template)

            # - Title -
            template = re.sub(r"__TITLE__", self.title.replace("&", "&amp;"), template)

            # - Subtitle -
            template = re.sub(r"__SUBTITLE__", self.subtitle.replace("&", "&amp;"), template)

            # - Description -
            template = re.sub(r"__DESCRIPTION__", self.description, template)

            # - Publication Year -
            template = re.sub(r"__DATE__", self.publication_year or "", template)

            # - Publisher -
            template = re.sub(r"__PUBLISHER__", self.publisher.replace("&", "&amp;") or "", template)

            # - Narrator -
            narrators=""
            for narrator in self.narrators:
                narrators += f"\t<dc:creator opf:role='nrt'>{narrator.name}</dc:creator>\n"
            template = re.sub(r"__NARRATORS__", narrators, template)

            # - ASIN -
            template = re.sub(r"__ASIN__", self.asin, template)

            # - ISBN -
            template = re.sub(r"__ISBN__", self.isbn or "", template)

            # - Series -
            series=""
            for s in self.series:
                series += f"\t<ns0:meta name='calibre:series' content='{s.name.replace("&", "&amp;")}' />\n"
                series += f"\t<ns0:meta name='calibre:series_index' content='{s.part.replace("&", "&amp;")}' />\n"
            template = re.sub(r"__SERIES__", series, template)

            # - Genres -
            genres=""
            for genre in self.genres:
                genres += f"\t<dc:subject>{genre.name.replace("&", "&amp;")}</dc:subject>\n"
            template = re.sub(r"__GENRES__", genres, template)

            # - Tags - 
            tags=""
            for tag in self.tags:
                tags += f"\t<dc:tag>{tag.name.replace("&", "&amp;")}</dc:tag>\n"
            template = re.sub(r"__TAGS__", tags, template)

            # - Language -
            template = re.sub(r"__LANGUAGE__", self.language, template)

            opfFile=os.path.join(path, "metadata.opf")
            with open(opfFile, mode='w', encoding='utf-8') as file:
                file.write(template)
        except Exception as e:
            print (f"Error creating OPF file {path}: {e}")

        return

    def sanitize_authors(self):
        # takes any authors in the instance and sanitizes the text. 
        if len(self.authors):
            authors = []
            for author in self.authors:
                #remove some characters we don't want on the author name
                stdAuthor=utils.strip_accents(author.name)

                #remove some characters we don't want on the author name
                for c in ["- editor", "- contributor", " - ", "'"]:
                    stdAuthor=stdAuthor.replace(c,"")

                #replace . with space, and then make sure that there's only single space between words)
                stdAuthor=" ".join(stdAuthor.replace("."," ").split())
                authors.append(stdAuthor)
            return authors

    def get_sanitized_title(self, strip_accents=True, remove_book_x=True, remove_subtitle=True):
        #remove (Unabridged) and strip accents
        clean_title:str = str(self.title)

        for token in [" (Unabridged)", "m4b", "mp3", ",", "- ", "_", "epub", "|", "(", ")"]:
            clean_title = clean_title.replace(token," ")
        
        if strip_accents:
            clean_title = utils.strip_accents(clean_title)

        #remove Book X
        if remove_book_x:
            clean_title = re.sub (r"\bBook(\s)?(\d)+\b", "", clean_title, flags=re.IGNORECASE)

        # remove any subtitle that goes after a :
        if remove_subtitle:
            clean_title = re.sub (r"(:(\s)?([a-zA-Z0-9_'\.\s]{2,})*)", "", clean_title, flags=re.IGNORECASE)

        return clean_title

    def standardizeAuthors(self, mediaPath, dryRun=False):
        #get all authors from the source path
        for f in iglob(os.path.join(mediaPath,"*"), recursive=False):
            #ignore @eaDir
            if (f != os.path.join(mediaPath,"@eaDir")):
                oldAuthor=os.path.basename(f)
                newAuthor=self.cleanseAuthor(oldAuthor)
                if (oldAuthor != newAuthor):
                    print(f"Renaming: {f} >> {os.path.join(os.path.dirname(f), newAuthor)}")
                    if (not dryRun):
                        try:
                            os.path(f).rename(os.path.join(os.path.dirname(f), newAuthor))
                        except Exception as e:
                            print (f"Can't rename {f}: {e}")
    
    def cleanseSeries(series):
        #remove colons
        cleanSeries = series
        for c in [":", "'"]:
            cleanSeries = cleanSeries.replace (c, "")

        return cleanSeries.strip()
    
    def isGraphicAudio(author):
        m = re.search(r"graphic[\s]?audio[\s]?(llc[.]?)*", author.lower())
        #print (f"Is {author} = 'Graphic Audio LLC.'? {m}")
        return (m is not None)

    def isThisMyAuthorsBook (self, authors, book, cfg):
        #Config
        verbose = bool(cfg.get("Config/flags/verbose"))

        found=False
        for author in authors:
            if self.isGraphicAudio(author.name): 
                continue
            else:
                for bauthor in book.authors:
                    if self.isGraphicAudio(bauthor.name): 
                        continue
                    else:
                        if verbose:
                            print (f"Checking if {book.title} is {authors}'s book: {book.authors}")

                        #print (f"Author: {author.name} = {bauthor.name}? {(author.name.replace(' ', '') == bauthor.name.replace(' ', ''))}")
                        if (self.cleanseAuthor(author.name).replace(" ", "") == self.cleanseAuthor(bauthor.name).replace(" ", "")):
                            #print ("found\n")
                            found=True
                            break
            
            if found: break

        return found

    def isThisMyBookTitle (self, title, book, cfg):
        #Config
        matchrate = int(cfg.get("Config/matchrate"))
        verbose = bool(cfg.get("Config/flags/verbose"))

        mytitle = self.cleanseTitle(title)
        thisTitle = self.cleanseTitle(book.title)
        thisSeriesTitle = thisTitle

        if len(book.series):
            thisSeries = self.cleanseSeries(book.series[0].name)
            thisSeriesTitle = " - ".join([thisSeries, thisTitle])
        
        matchname = utils.fuzzymatch(mytitle, thisTitle)
        matchseriesname = utils.fuzzymatch(mytitle, thisSeriesTitle)
        if verbose:
            print (f"Checking if {thisTitle} or {thisSeriesTitle} matches my book {mytitle}: {matchname} or {matchseriesname}")

        #see if any of the fuzzy match scores are within guidance
        match=False
        for k in matchname.keys():
            if matchname[k] >= matchrate:
                match=True
                break

        if not match:
            for k in matchseriesname.keys():
                if matchseriesname[k] >= matchrate:
                    match=True
                    break

        return match

    def getList(self, items, delimiter=","):
        enclosedItems=[]
        for item in items:
            if type(item) == Contributor_Entity:
                enclosedItems.append(self.cleanseAuthor(item.name))
            else:
                if type(item) == Series_Entity:
                    enclosedItems.append(self.cleanseSeries(item.name))
                else:
                    enclosedItems.append(item.name)

        return delimiter.join(enclosedItems)
        
    def getAltTitle(self, parent, book, cfg):
        #Config
        verbose = bool(cfg.get("Config/flags/verbose"))
        patterns = cfg.get ("Config/tokens/title_patterns")
        skipSeries = bool (cfg.get ("Config/tokens/skip_series"))

        stop = False
        words = []
        
        #start with title
        altTitle = self.cleanseTitle(book.title).lower()

        #if title is blank, use series?
        if (len(altTitle) == 0) and (len(book.series)):
            altTitle = self.cleanseTitle(book.series[0].name)
            if len(altTitle) : skipSeries = True

        print (f"Proxwaaing {altTitle}")
        while True:
            #remove authors name in title
            for a in book.authors:
                altTitle = re.sub(f"{a.name}", " ", altTitle, flags=re.IGNORECASE)
                #print (f"remove {book.authors} >> {altTitle}")

            #remove series name in title
            if (not skipSeries):
                for s in book.series:
                    altTitle = re.sub(f"{s.name}", " ", altTitle, flags=re.IGNORECASE)
                #print (f"remove {book.series} >> {altTitle}")

            #remove the numbers
            altTitle = re.sub(r"\b\d*\b", "", altTitle, flags=re.IGNORECASE)
            #print (f"remove digits >> {altTitle}")

            #remove extra characters (there really should'nt be : here) 
            for c in patterns:
                #c = str.replace (c, "\\", "\")
                regx =re.compile(c, re.IGNORECASE)
                #print (f"{regx} = {altTitle}")
                altTitle = regx.sub(" ", altTitle)
                #altTitle = altTitle.replace (c, " ")

            for c in ["'", "-"]:
                altTitle = altTitle.replace (c, "")
                #print (f"remove symbols >> {altTitle}")

            for w in altTitle.split():
                if w not in words:
                    words.append(w)

            #print (f"remove spaces >> {' '.join(words)}")
            if (len(words)) or (stop):
                altTitle = ' '.join(words)
                book.title = altTitle

                if verbose:
                    print (f"Found alternative title: {altTitle}")
                break

            else:
                altTitle = self.cleanseTitle(parent).lower()
                stop = True

        #join the title back
        if len (words):
            return book.title
        else:
            return ""