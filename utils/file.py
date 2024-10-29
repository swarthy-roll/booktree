from glob import iglob
import os, re

def get_all_files(path, file_types):
    files = []
    try:
        for f in file_types:
            print (f"Looking for: {f.split(".")[-1]} in {path}")
            files.extend(iglob(f, root_dir=path, recursive=True))

        return files
        
    except Exception as e:
        print(f"ERROR: Error while fetching all the files of type {f}. Error message: {e}")

    


def isMultiBookCollection(filePath):
    #Is this MAM result a collection
    isMBC = False
    #if the # of paths from source path is 3 or more
    path, file = os.path.split(filePath)    
    #how deep is it from the source?
    filedepth = len(path.split(os.sep)) + 1
    #print (f"File depth of {filePath} is {filedepth}")
    # if the filedepth from source is 3 levels down, assume it's a multibook collection
    isMBC = (filedepth >= 3)
    return isMBC

def isMultiCD(parent):
    return re.search(r"disc\s?\d+", parent.lower()) or re.search(r"cd\s?\d+", parent.lower())