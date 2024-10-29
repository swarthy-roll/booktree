from dataclasses import dataclass, field
from glob import iglob
from enum import Enum
from utils import utils
import entities.series as s, entities.contributor as contributor, entities.category as category
import entities.genre as g
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
    publication_name:str=""
    publisher:str=""
    length:int=0
    duration:float=0
    matchRate:int=0
    language:str="English"
    snatched:bool=False
    description:str=""
    series:list[s.Series]= field(default_factory=list)
    authors:list[contributor.Contributor]= field(default_factory=list)
    narrators:list[contributor.Contributor]= field(default_factory=list)
    genres:list[category.Categories]= field(default_factory=list)
    tags:list[category.Categories]= field(default_factory=list)
    files:list[str]= field(default_factory=list)
    source:Source=0

    def __init__(self, source:Source):
        self.source = source

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
    
    def getAuthors(self, delimiter=",", encloser="", stripaccents=True):
        if len(self.authors):
            return utils.getList(self.authors, delimiter, encloser, stripaccents=True)
        else:
            return ""
    
    def getSeries(self, delimiter=",", encloser="", stripaccents=True):
        if len(self.series):
            return utils.getList(self.series, delimiter, encloser, stripaccents=True)
        else:
            return ""
    
    def getNarrators(self, delimiter=",", encloser="", stripaccents=True):
        if len(self.narrators):
            return utils.getList(self.narrators, delimiter, encloser, stripaccents=True) 
        else:
            return ""
        
    def getGenres(self, delimiter=",", encloser="", stripaccents=True):
        if len(self.genres):
            return utils.getList(self.genres, delimiter, encloser, stripaccents=True) 
        else:
            return ""

    def getTags(self, delimiter=",", encloser="", stripaccents=True):
        if len(self.tags):
            return utils.getList(self.tags, delimiter, encloser, stripaccents=True) 
        else:
            return ""
    
    def getSeriesParts(self, delimiter=",", encloser="", stripaccents=True):
        seriesparts = []
        for s in self.series:
            if len(s.name.strip()):
                seriesparts.append(contributor.Contributor(f"{s.name} {s.separator}{s.part}")) 
            
        return utils.getList(seriesparts, delimiter, encloser, stripaccents=True) 
    
    def setAuthors(self, authors):
        #Given a csv of authors, convert it to a list
        if len(authors.strip()):
            for author in authors.split (","):
                self.authors.append(contributor.Contributor(author))

    def setNarrators(self, narrators):
        #Given a csv of narrators, convert it to a list
        if len(narrators.strip()):
            for narrator in narrators.split (","):
                self.narrators.append(contributor.Contributor(narrator))

    def setGenres(self, genres, limit=2):
        #Given a csv of genres, convert it to a list. Default is two, fiction/nonfiction use one of the default spots
        if len(genres.strip()):
            if any(genre in genres for genre in g.fiction):
                self.genres.append(category.Categories("Fiction"))
            elif any(genre in genres for genre in g.nonfiction):
                self.genres.append(category.Categories("Nonfiction"))
            else: 
                self.genres.append(category.Categories("Unknown"))

            for genre in [genre for genre in genres.split(",") if genre not in g.top_level_genres][:limit-1]:
                self.genres.append(category.Categories(genre))

    def setTags(self, tags):
        #Given a csv of tags, convert it to a list
        for tag in [tag for tag in tags.split(",") if tag not in g.top_level_genres]:
            self.tags.append(category.Categories(tag))

    def setSeries(self, series):
        #Given a csv of series, convert it to a list
        #print (f"Parsing series {series}")
        if len(series.strip()):
            for s in list([series]):
                p = s.split("#")
                #print (f"Series: {s}\nSplit: {p}")
                if len(p) > 1: 
                    self.series.append(s.Series(str(p[0]).strip(), str(p[1]).strip()))
                else:
                    self.series.append(s.Series(str(p[0]).strip(), ""))
    
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


    def cleanseAuthor(author):
        #remove some characters we don't want on the author name
        stdAuthor=utils.strip_accents(author)

        #remove some characters we don't want on the author name
        for c in ["- editor", "- contributor", " - ", "'"]:
            stdAuthor=stdAuthor.replace(c,"")

        #replace . with space, and then make sure that there's only single space between words)
        stdAuthor=" ".join(stdAuthor.replace("."," ").split())
        return stdAuthor

    def cleanseTitle(title="", stripaccents=True, stripUnabridged=False):
        #remove (Unabridged) and strip accents
        stdTitle=str(title)

        for w in [" (Unabridged)", "m4b", "mp3", ",", "- ", "_", "epub"]:
            stdTitle=stdTitle.replace(w," ")
        
        if stripaccents:
            stdTitle = utils.strip_accents(stdTitle)

        #remove Book X
        stdTitle = re.sub (r"\bBook(\s)?(\d)+\b", "", stdTitle, flags=re.IGNORECASE)

        # remove any subtitle that goes after a :
        stdTitle = re.sub (r"(:(\s)?([a-zA-Z0-9_'\.\s]{2,})*)", "", stdTitle, flags=re.IGNORECASE)

        return stdTitle

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

    def getList(self, items, delimiter=",", encloser="", stripaccents=True):
        enclosedItems=[]
        for item in items:
            if type(item) == contributor.Contributor:
                enclosedItems.append(f"{encloser}{self.cleanseAuthor(item.name)}{encloser}")
            else:
                if type(item) == s.Series:
                    enclosedItems.append(f"{encloser}{self.cleanseSeries(item.name)}{encloser}")
                else:
                    enclosedItems.append(f"{encloser}{item.name}{encloser}")

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