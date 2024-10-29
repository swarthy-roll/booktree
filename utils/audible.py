import utils
from ..entities import book as book_entity
from ..entities import contributor as contributor_entity
from ..entities import series as series_entity

def getAudibleBooks(self, client, book, cfg):
        #Config variables
        minMatchRate = int(cfg.get("Config/matchrate"))
        fixid3 = bool(cfg.get("Config/flags/fixid3"))
        verbose = bool(cfg.get("Config/flags/verbose"))
        add_narrators = bool(cfg.get("Config/flags/add_narrators"))
        fuzzy_match = cfg.get("Config/fuzzy_match")

        books=[]
        if (book is not None):
            language=book.language
            # book = self.ffprobeBook
            if (len(book.title) == 0) or (fixid3):
                book.title = utils.getAltTitle (self.name, book, cfg) 
                
            title = utils.cleanseTitle(book.title, stripUnabridged=True)

            #sometimes Audible returns nothing if there's too much info in the keywords
            series=""
            if (len(book.series)==1):
                series = utils.cleanseTitle(book.getSeries(), stripUnabridged=True)
            elif len(book.series):
                series = utils.cleanseTitle(book.series[0].name, stripUnabridged=True)
            
            if add_narrators:
                keywords=utils.optimizeKeys(cfg, [utils.cleanseTitle(title, stripUnabridged=True), 
                                                    series,
                                                    utils.cleanseAuthor(book.getAuthors(delimiter=" ")), 
                                                    utils.cleanseAuthor(book.getNarrators(delimiter=" "))])
            else:
                keywords=utils.optimizeKeys(cfg, [utils.cleanseTitle(title, stripUnabridged=True), 
                                                    series,
                                                    utils.cleanseAuthor(book.getAuthors(delimiter=" "))])

            #print(f"Searching Audible for\n\tasin:{book.asin}\n\ttitle:{title}\n\tauthors:{book.authors}\n\tnarrators:{book.narrators}\n\tkeywords:{keywords}")
            
            #generate author, narrator combo
            author_narrator=[]
            for i in range(len(book.authors)):
                if add_narrators and len(book.narrators):
                    for j in range(len(book.narrators)):
                        author_narrator.append((book.authors[i].name, book.narrators[j].name))
                else:
                        author_narrator.append((book.authors[i].name, ""))

            #print (author_narrator)

            for an in author_narrator:
                #print (f"Author: {an[0]}\tNarrator: {an[1]}")
                sAuthor=utils.cleanseAuthor(an[0])
                sNarrator=utils.cleanseAuthor(an[1])
                books=getAudibleBook (client, cfg, asin=book.asin, title=title, authors=sAuthor, narrators=sNarrator, keywords=keywords, language=language)

                #book found, exit for loop
                if ((books is not None) and len(books)):
                    break
                
            #too constraining?  try just a keywords search with all information
            if ((books is None) or ((books is not None) and (len(books) == 0))):
                #print (f"Nothing was found so just doing a keyword search {keywords}")
                books=getAudibleBook (client, cfg, keywords=keywords, language=language)

            mamBook = '|'.join([f"Duration:{self.getRunTimeLength()}min", book.getAuthors(), book.getCleanTitle(), series])
            if add_narrators:
                mamBook = '|'.join([mamBook, book.getNarrators()])

            #process search results
            self.audibleMatches=books
            if (self.audibleMatches is not None):
                if (verbose):
                    print(f"Found {len(self.audibleMatches)} Audible match(es)\n\n")

                bestMatchRate=0
                #find the best match
                print(f"Finding the best Audible match out of {len(books)} results")
                for product in books:
                    abook=product2Book(product)
                    #the author is known, check if this book is this authors book
                    #otherwise, if maybe this title is close enough
                    #print (f"{abook.title} by {abook.authors}...")
                    if len(book.authors) and utils.isThisMyAuthorsBook(book.authors, abook, cfg):
                        audibleBook = '|'.join([f"Duration:{abook.length}min", abook.getAuthors(), abook.getCleanTitle(), abook.getSeriesParts()])
                        if add_narrators:
                            audibleBook = '|'.join([audibleBook, abook.getNarrators()])
                    elif utils.isThisMyBookTitle(title, abook, cfg): 
                        audibleBook = '|'.join([f"Duration:{abook.length}min", abook.getAuthors(), abook.getCleanTitle(), abook.getSeriesParts()])
                        if add_narrators:
                            audibleBook = '|'.join([audibleBook, abook.getNarrators()])
                    else:
                        print (f"This book doesn't have a matching title or author, checking the next book...")
                        continue        

                    #include this book in the comparison
                    matchRate=utils.fuzzymatch(mamBook, audibleBook)
                    abook.matchRate=matchRate[fuzzy_match]

                    print(f"\tMatch Rate: {matchRate}\n\tSearch: {mamBook}\n\tResult: {audibleBook}\n\tBest Match Rate: {bestMatchRate}\n")
                    
                    if (matchRate[fuzzy_match] > bestMatchRate) and (matchRate[fuzzy_match] >= minMatchRate):
                        bestMatchRate=matchRate[fuzzy_match]
                        self.bestAudibleMatch=abook
        #end if

        #pprint(self.bestAudibleMatch)
        if (books is not None): 
            #pprint (books)            
            return self.bestAudibleMatch
        else: 
            return None

def getAudibleBook(client, cfg, asin="", title="", authors="", narrators="", keywords="", language="english"):
    print (f"Searching Audible for\n\tasin:{asin}\n\ttitle:{title}\n\tauthors:{authors}\n\tnarrators:{narrators}\n\tkeywords:{keywords}")

    enBooks=[]
    cacheKey = utils.getHash(f"{asin}{title}{authors}{narrators}{keywords}")
    books={}
    if utils.isCached(cacheKey, "audible", cfg):
        print (f"Retrieving {cacheKey} from audible")

        #this search has been done before, retrieve the results
        books = utils.loadFromCache(cacheKey, "audible")

    else:
        try:
            if len(asin) : 
                p=f"https://api.audible.com/1.0/catalog/products/{asin}"
            else:
                p=f"https://api.audible.com/1.0/catalog/products"

            r = client.get (
                p,
                params={
                    "asin": asin,
                    "title": title,
                    "author": authors,
                    "narrator": narrators,
                    "keywords": keywords,
                    "products_sort_by": "Relevance",
                    "response_groups": (
                        "series, product_attrs, relationships, contributors, product_desc, product_extended_attrs"
                    )
                },
            )

            r.raise_for_status()
            books = r.json()

            #cache this results
            utils.cacheMe(cacheKey, "audible", books, cfg)

        except Exception as e:
                print(f"Error searching audible: {e}")

    
    #check for ["product"] or ["products"]
    if "product" in books.keys():
        enBooks.append(books["product"])
    elif "products" in books.keys():
        for book in books["products"]:
            #ignore non-english books
            if ("language" in book) and (book["language"] == language):
                enBooks.append(book)

    return enBooks

def product2Book(product):
    #product is an Audible product json
    if product is not None:
        book=book_entity.Book()
        if 'asin' in product: book.asin=str(product["asin"])
        if 'title' in product: book.title=str(product["title"])
        if 'subtitle' in product: book.subtitle=str(product["subtitle"])
        if 'publisher_summary' in product: book.description=str(product["publisher_summary"])
        if 'runtime_length_min' in product: book.length=product["runtime_length_min"]
        if 'authors' in product: 
            for author in product["authors"]:
                book.authors.append(contributor_entity.Contributor(str(author["name"])))
        if 'narrators' in product: 
            for narrator in product["narrators"]:
                book.narrators.append(contributor_entity.Contributor(str(narrator["name"])))
        if 'publication_name' in product: book.publicationName=str(product["publication_name"])
        if 'series' in product: 
            for s in product["series"]:
                book.series.append(series_entity.Series(str(s["title"]), str(s["sequence"])))
        if 'language' in product: book.language=str(product ["language"])

            
        return book
    else:
        return None