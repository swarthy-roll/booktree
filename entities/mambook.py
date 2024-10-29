from dataclasses import field
from ..utils import utils
import os, re, requests, json, pickle, math
import entities.book as book_entity
import entities.series as series_entity
import entities.bookfile as bookfile_entity
import entities.contributor as contributor_entity

class MAMBook:
    name:str
    files:list= field(default_factory=list) 
    ffprobeBook:book_entity.Book=None
    bestAudibleMatch:book_entity.Book=None 
    bestMAMMatch:book_entity.Book=None
    mamMatches:list[book_entity.Book]= field(default_factory=list)    
    audibleMatches:list[book_entity.Book]= field(default_factory=list)  
    isSingleFile:bool=False
    isMultiFileBook:bool=False
    isMultiBookCollection:bool=False
    metadata:str="id3"
    metadataBook:book_entity.Book=None
    paths:str=""
    isMatched:bool=False

    def getRunTimeLength(self):
        #add all the duration of the files in the book, and convert into minutes
        duration:float=0
        for f in self.files:
            duration += float(f.ffprobeBook.duration)

        return math.floor(duration/60)

    def ffprobe(self, file):
        #ffprobe the file
        metadata=None
        book=None
        
        try:
            metadata=utils.probe_file(file)["format"]["tags"]
        except Exception as e:
            #ignore errors
            print ("", end="")
            #print (f"\nffprobe failed on {self.name}: {e}")

        if (metadata is not None):
            #parse and create a book object
            # format|tag:title=In the Likely Event (Unabridged)|tag:artist=Rebecca Yarros|tag:album=In the Likely Event (Unabridged)|tag:AUDIBLE_ASIN=B0BXM2N523
            #{'format': {'tags': {'title': 'MatchUp', 'artist': 'Lee Child - editor, Val McDermid, Charlaine Harris, John Sandford, Kathy Reichs', 'composer': 'Laura Benanti, Dennis Boutsikaris, Gerard Doyle, Linda Emond, January LaVoy, Robert Petkoff, Lee Child', 'album': 'MatchUp'}}}
            book=book.Book()
            if 'AUDIBLE_ASIN' in metadata: book.asin=metadata["AUDIBLE_ASIN"]
            if 'title' in metadata: book.title=metadata["title"]
            if 'subtitle' in metadata: book.subtitle=metadata["subtitle"]
            #series and part, if provided
            if (('SERIES' in metadata) and ('PART' in metadata)): 
                book.series.append(series_entity.Series(metadata["SERIES"],metadata["PART"]))
            #parse album, assume it's a series
            if 'album' in metadata: book.series.append(series_entity.Series(metadata["album"],""))
            #parse authors
            if 'artist' in metadata: 
                #remove everything in parentheses firstm before parsing
                artist = metadata["artist"]
                for author in re.split(",", artist):
                    author = re.sub(r"\([.]+\)", "", author, flags=re.IGNORECASE)  
                    author = utils.removeGA(author)
                    if len(author): book.authors.append(contributor_entity.Contributor())
            #parse narrators
            if 'composer' in metadata: 
                composer = metadata["composer"]
                for narrator in re.split(",", composer):
                    #remove any occurrence of (Narrator)
                    narrator = re.sub(r"\([.]+\)", "", narrator, flags=re.IGNORECASE)       
                    book.narrators.append(contributor_entity.Contributor(narrator))
        
        #return a book object created from  ffprobe
        self.ffprobeBook=book

        return book
        
    def createHardLinks(self, cfg):
        #Config variables
        dryRun = bool (cfg.get("Config/flags/dry_run"))
        verbose = bool (cfg.get("Config/flags/verbose"))
        no_opf = bool (cfg.get("Config/flags/no_opf"))
        metadata = cfg.get("Config/metadata")

        if (self.metadata == "audible"):
            self.metadataBook=self.bestAudibleMatch
        elif (self.metadata == "mam"):
            self.metadataBook=self.bestMAMMatch
        else:
            self.metadataBook=self.ffprobeBook

        if (self.metadataBook is not None):
            if (dryRun):
                prefix = "[Dry Run] : "    
            else:
                prefix = ""    

            #for each file for this book                
            for f in self.files:
                #UPDATED 8/30 to allow users to customize target_path formats  
                if metadata == "log":
                    p = self.paths
                else:
                    p = f.getConfigTargetPath(cfg, self.metadataBook)

                print (f"{prefix}Hardlinking files for {self.metadataBook.title}")
                print (f"\t\t\tfrom {f.fullPath}\n\t\t\t  to {p}")

                if (not dryRun):
                    #hardlink the file
                    f.hardlinkFile(f.fullPath, p)                   

                    #generate the OPF file
                    print (f"\tGenerating OPF file ...")
                    if (not no_opf):
                        self.metadataBook.createOPF(p)

    def matchFound(self):
        return bool(((self.bestMAMMatch is not None) or (self.bestAudibleMatch is not None)))
    
    def getLogRecord(self, bf, cfg):
        #MAMBook fields
        book={}
        book["book"]=self.name
        book["file"]=bf.fullPath
        book["sourcePath"]=bf.sourcePath
        book["mediaPath"]=bf.mediaPath
        book["isMatched"]=self.isMatched
        book["isHardLinked"]= bf.isHardlinked
        book["mamCount"]=len(self.mamMatches)
        book["audibleMatchCount"]=len(self.audibleMatches)
        book["metadatasource"]=self.metadata

        #check out the targetpath of the bookfile
        if book["metadatasource"] != "as-is":
            book["paths"]=bf.getConfigTargetPath(cfg, self.metadataBook)

        #Get FFProbe Book
        if (bf.ffprobeBook is not None):
            book=bf.ffprobeBook.getDictionary(book, "id3-")

        #Get MAM Book
        if (self.bestMAMMatch is not None):
            book=self.bestMAMMatch.getDictionary(book, "mam-")

        #Get Audible Book
        if (self.bestAudibleMatch is not None):
            book=self.bestAudibleMatch.getDictionary(book, "adb-")

        return book    
    
    #MAM Functions
    def searchMAM(cfg, titleFilename, authors, extension):
        #Config
        session = cfg.get("Config/session")
        log_path = cfg.get("Config/log_path")
        ebook = bool(cfg.get("Config/flags/ebooks"))
        audiobook = not (ebook)
        
        #put paren around authors and titleFilename
        if len(authors):
            authors = f"({authors})"

        if len(titleFilename):
            titleFilename = f"({titleFilename})"

        search = f'{authors} {titleFilename} {extension} @dummy mamDummy'

        #cache results for this search string
        cacheKey=utils.getHash(search)
        
        if utils.isCached(cacheKey, "mam", cfg):
            #this search has been done before, load results from cache
            results = utils.loadFromCache(cacheKey, "mam")
            return (results["data"])
        
        else:
            #save cookie for future use
            cookies_filepath = os.path.join(log_path, 'cookies.pkl')
            sess = requests.Session()

            #a cookie file exists, use that
            if os.path.exists(cookies_filepath):
                cookies = pickle.load(open(cookies_filepath, 'rb'))
                sess.cookies = cookies
            else:
                #assume a session ID is passed as a parameter
                sess.headers.update({"cookie": f"mam_id={session}"})

            #test session and cookie
            r = sess.get('https://www.myanonamouse.net/jsonLoad.php', timeout=5)  # test cookie
            if r.status_code != 200:
                raise Exception(f'Error communicating with API. status code {r.status_code} {r.text}')
            else:
                # save cookies for later
                with open(cookies_filepath, 'wb') as f:
                    pickle.dump(sess.cookies, f)

                mam_categories = []
                if audiobook:
                    mam_categories.append(13) #audiobooks
                    mam_categories.append(16) #radio
                if ebook:
                    mam_categories.append(14)
                if not mam_categories:
                    return None
                
                params = {
                    "tor": {
                        "text": search,  # The search string.
                        "srchIn": {
                            "title": "true",
                            "author": "true",
                            "fileTypes": "true",
                            "filenames": "true"
                        },
                        "main_cat": mam_categories
                    },
                    "perpage":50
                }

                try:
                    r = sess.post('https://www.myanonamouse.net/tor/js/loadSearchJSONbasic.php', json=params)
                    if r.text == '{"error":"Nothing returned, out of 0"}':
                        return None

                    results = r.json()

                    #cache this result before returning it
                    utils.cacheMe(cacheKey, "mam", results, cfg)

                    return (results["data"])
            
                except Exception as e:
                    print(f'error searching MAM {e}')

        return None

    def getMAMBook(self, cfg, titleFilename="", authors="", extension=""):
        books=[]
        mamBook=self.searchMAM(cfg, titleFilename, authors, extension)
        if (mamBook is not None):
            for mb in mamBook:
                #pprint(mb)
                book=book_entity.Book()
                book.init()
                if 'asin' in mb: 
                    book.asin=str(mb["asin"])
                if 'title' in mb: 
                    book.title=str(mb["title"])
                if 'author_info'in mb:
                    #format {id:author, id:author}
                    if len(mb["author_info"]):
                        authors = json.loads(mb["author_info"])
                        for author in authors.values():
                            book.authors.append(contributor_entity.Contributor(str(author)))
                if 'series_info'in mb:
                    #format {"35598": ["Kat Dubois", "5"]}
                    if len(mb["series_info"]):
                        series_info = json.loads(mb["series_info"])
                        for series in series_info.values():
                            s=list(series)
                            book.series.append(series_entity.Series(str(s[0]), s[1]))    
                if 'lang_code' in mb: 
                    book.language=utils.getLanguage((mb["lang_code"]))
                if 'my_snatched' in mb:
                    book.snatched=bool((mb["my_snatched"])) 
                
                if book.snatched:
                    books.append(book)

        return books

    def getMAMBooks(self, cfg, bookFile:bookfile_entity.BookFile):
        #Config variables
        verbose = bool(cfg.get("Config/flags/verbose"))
        ebooks = bool(cfg.get("Config/flags/ebooks"))
        add_narrators = bool(cfg.get("Config/flags/add_narrators"))
        fuzzy_match = cfg.get("Config/fuzzy_match")

        #search MAM record for this book
        title = f'"{bookFile.getFileName()}"'
        authors=self.ffprobeBook.getAuthors(delimiter="|", encloser='"', stripaccents=False)
        extension = f'"{bookFile.getExtension()}"'
    
        # Search using book key and authors (using or search in case the metadata is bad)
        print(f"Searching MAM for\n\tTitleFilename: {title}\n\tauthors:{authors}")
        books=self.getMAMBook(cfg, titleFilename=title, authors=authors, extension=extension)

        # was the author inaccurate? (Maybe it was LastName, FirstName or accented)
        # print (f"Trying again because Filename, Author = {len(self.mamMatches)}")
        if len(books) == 0:
            #try again, without author this time
            print(f"Widening MAM search using just\n\tTitleFilename: {title}")
            books=self.getMAMBook(cfg, titleFilename=title, extension=extension)

        #Find the best match
        self.mamMatches = books
        book = self.ffprobeBook

        if (not ebooks) and (self.mamMatches is not None) and (book is not None):
            if (verbose):
                print(f"Found {len(self.mamMatches)} MAM match(es)\n\n")

            bestMatchRate=0
            #find the best match
            print(f"Finding the best MAM match out of {len(books)} results")
            targetBook = '|'.join([self.ffprobeBook.title, self.ffprobeBook.getAuthors(), self.ffprobeBook.getSeriesParts()])
    
            for abook in books:
                #if this book is snatched, include in the match
                if abook.snatched:
                    #the author is known, check if this book is this authors book
                    #otherwise, if maybe this title is close enough
                    #print (f"{abook.title} by {abook.authors}...")
                    if len(book.authors) and utils.isThisMyAuthorsBook(book.authors, abook, cfg):
                        mamBook = '|'.join([abook.getAuthors(), abook.getCleanTitle(), abook.getSeriesParts()])
                        if add_narrators:
                            mamBook = '|'.join([mamBook, abook.getNarrators()])
                    elif utils.isThisMyBookTitle(title, abook, cfg): 
                        mamBook = '|'.join([abook.getAuthors(), abook.getCleanTitle(), abook.getSeriesParts()])
                        if add_narrators:
                            mamBook = '|'.join([mamBook, abook.getNarrators()])
                    else:
                        print (f"This book doesn't have a matching title or author, checking the next book...")
                        continue        

                    #include this book in the comparison
                    matchRate=utils.fuzzymatch(targetBook, mamBook)
                    abook.matchRate=matchRate[fuzzy_match]

                    print(f"\tMatch Rate: {matchRate}\n\tSearch: {targetBook}\n\tResult: {mamBook}\n\tBest Match Rate: {bestMatchRate}\n")
                    
                    if (matchRate[fuzzy_match] > bestMatchRate):
                        bestMatchRate=matchRate[fuzzy_match]
                        self.bestMAMMatch=abook
        else:
            #no metadata, get the first match?
            if len(self.mamMatches):
                self.bestMAMMatch = books[0]


        #pprint(self.bestMAMMatch)
        if (books is not None): 
            return self.bestMAMMatch
        else: 
            return None
    
    def getHashKey(self):
        return utils.getHash(self.name)

    def isCached(self, category, cfg):
        return utils.isCached(self.getHashKey(),category, cfg)
        
    def cacheMe(self, category, content, cfg):
        return utils.cacheMe(self.getHashKey(),category, content, cfg) 
        
    def loadFromCache(self, category):
        return utils.loadFromCache(self.getHashKey(), category)