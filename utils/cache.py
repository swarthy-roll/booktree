
import os, json, hashlib

def getHash(key):
    return hashlib.sha256(key.encode(encoding="utf-8")).hexdigest()

def isCached(key, category, cfg):
    #Config
    verbose = bool(cfg.get("Config/flags/verbose"))

    if verbose:
        print (f"Checking cache: {category}/{key}...")
    
    #Check if this book's hashkey exists in the cache, if so - it's been processed
    bookFile = os.path.join(os.getcwd(), "__cache__", category, key)
    found = os.path.exists(bookFile)  
    return found      
    
def cacheMe(key, category, content, cfg):
    #Config
    verbose = bool(cfg.get("Config/flags/verbose"))

    #create the cache file
    bookFile = os.path.join(os.getcwd(), "__cache__", category, key)
    with open(bookFile, mode="w", encoding='utf-8', errors='ignore') as file:
        file.write(json.dumps(content))

    if verbose:
        print(f"Caching {key} in File: {bookFile}")
    return os.path.exists(bookFile)        

def loadFromCache(key, category):
    #return the content from the cache file
    bookFile = os.path.join(os.getcwd(), "__cache__", category, key)
    with open(bookFile, mode='r', encoding='utf-8') as file:
        f = file.read()
    
    return json.loads(f)
