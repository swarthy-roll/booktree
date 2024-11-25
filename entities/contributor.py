from dataclasses import dataclass
from utils.utils import strip_accents
from model.contributor import Contributor as Contributor_Model

@dataclass
class Contributor:
    name:str

    def save(self):
        contributor, result = Contributor_Model.get_or_create(**self.__dict__)
        return contributor

    def removeGA (author:str):
        #remove Graphic Audio and special characters like ()[]
        cleanAuthor = author.replace("GraphicAudio","").replace("[","").replace("]","")
        return cleanAuthor.strip()
    
    def get_clean_name(self):
        clean_name = strip_accents(self.name)

        #remove some characters we don't want on the author name
        for c in ["- editor", "- contributor", " - ", "'"]:
            clean_name = clean_name.replace(c,"")

        #replace . with space, and then make sure that there's only single space between words)
        clean_name = " ".join(clean_name.replace("."," ").split())

        return clean_name