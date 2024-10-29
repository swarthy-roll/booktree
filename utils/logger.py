
def logBooks(logFilePath, books, cfg):
    if len(books):
        write_headers = not os.path.exists(logFilePath)
        with open(logFilePath, mode="a", newline="", errors='ignore') as csv_file:
            try:
                fields=getLogHeaders()
                #pprint (fields)
                for book in books:
                    for file in book.files:
                        row=book.getLogRecord(file,cfg)
                        #pprint(row)
                        #create a writer
                        writer = csv.DictWriter(csv_file, fieldnames=fields)
                        if write_headers:
                            writer.writeheader()
                            write_headers=False
                        writer.writerow(row)

            except csv.Error as e:
                print(f"file {logFilePath}: {e}")

def readLog(logFilePath, books):
    if os.path.exists(logFilePath):
        with open(logFilePath, newline="", errors='ignore', encoding='utf-8',) as csv_file:
            try:
                reader = csv.reader(csv_file,)
                for row in reader:
                    ##Create a new Book
                    print(row)
                    print(reader.fieldnames)

            except csv.Error as e:
                print(f"file {logFilePath}: {e}")

def getLogHeaders():
    headers=['book', 'file', 'paths', 'isMatched', 'isHardLinked', 'mamCount', 'audibleMatchCount', 'metadatasource'
             , 'id3-matchRate', 'id3-asin', 'id3-title', 'id3-subtitle', 'id3-publicationName', 'id3-length', 'id3-duration', 'id3-series', 'id3-authors', 'id3-narrators', 'id3-seriesparts', 'id3-language', 'id3-isbn', 'id3-tags', 'id3-genres'
             , 'mam-matchRate', 'mam-asin', 'mam-title', 'mam-subtitle', 'mam-publicationName', 'mam-length', 'mam-duration', 'mam-series', 'mam-authors', 'mam-narrators', 'mam-seriesparts', 'mam-language', 'mam-isbn', 'mam-tags', 'mam-genres'
             , 'adb-matchRate', 'adb-asin', 'adb-title', 'adb-subtitle', 'adb-publicationName', 'adb-length', 'adb-duration', 'adb-series', 'adb-authors', 'adb-narrators', 'adb-seriesparts', 'adb-language'
             , 'sourcePath', 'mediaPath']
                    
    return dict.fromkeys(headers)

def printDivider (char="-", length=40):
    print("\n", length * char, "\n")


def logBookRecords(logFilePath, bookFiles, cfg):

    write_headers = not os.path.exists(logFilePath)
    with open(logFilePath, mode="a", newline="", errors='ignore') as csv_file:
        try:
            for f in bookFiles:
                #get book records to log
                if (f.isMatched):
                    row=f.getLogRecord(f.audibleMatch, cfg)
                else:
                    row=f.getLogRecord(f.ffprobeBook, cfg)
                #get fieldnames
                row["matches"]=len(f.audibleMatches)
                fields=row.keys()

                #create a writer
                writer = csv.DictWriter(csv_file, fieldnames=fields)
                if write_headers:
                    writer.writeheader()
                    write_headers=False
                writer.writerow(row)

        except csv.Error as e:
            print(f"file {logFilePath}: {e}")