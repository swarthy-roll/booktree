
import unicodedata
from thefuzz import fuzz
import re
from langcodes import *

#Utilities
def fuzzymatch(x:str, y:str):
    newX = x
    newY = y
    newZ = {"partial" : 0, "token_sort" : 0, "ratio" : 0}
    #remove .:_-, for fuzzymatch
    for c in [".", ":", "_", "-", "[", "]", "'"]:
        newX = newX.replace (c, "")
        newY = newY.replace (c, "")

    if (len(newX) and len(newY)):
        newZ["partial"]=fuzz.partial_ratio(newX, newY)
        newZ["token_sort"]=fuzz.token_sort_ratio(newX, newY)
        newZ["ratio"]=fuzz._ratio(newX, newY)

    return newZ
    
def optimizeKeys(cfg, keywords, delim=" "):
    #Config Variables
    kw_ignore = cfg.get("Config/tokens/kw_ignore")
    kw_ignore_words = cfg.get("Config/tokens/kw_ignore_words")

    #keywords is a list of stuff, we want to convert it in a comma delimited string
    kw=[]
    for k in keywords:
        for c in kw_ignore: #[".", ":", "_", "[", "]", "{", "}", ",", ";", "(", ")"]:
            k = k.replace(c, " ")

        #print(k)
        #parse this item "-"
        for i in k.split("-"):
            #parse again on spaces
            #print(i)
            for j in i.split():
                #print(j)
                #if it's numeric like 02, make it an actual digit
                if (len(j) > 1):
                    lcj = j.lower()
                    #if not an article, or a word in the ignore list
                    if lcj not in kw_ignore_words: #["the","and","m4b","mp3","series","audiobook","audiobooks", "book", "part", "track", "novel"]:
                        #if not CD or DISC XX"
                        if not (re.search (r"cd\s?\d+", j, re.IGNORECASE) or  re.search (r"disc\s?\d+", j, re.IGNORECASE)):
                            #if not a number
                            if not (re.search (r"\d+", j, re.IGNORECASE)):
                                #if it's not already in the list
                                if lcj not in kw:
                                    kw.append(j.lower())

    #now return comma delimited string
    return delim.join(kw)

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                    if unicodedata.category(c) != 'Mn')

def getLanguage(code):
    lang = "english"
    try: 
        lang = Language.get(code).display_name()

    except:
        print ("Unable to get display name for Language: {code}, defaulting to English")
    
    return lang.lower()

