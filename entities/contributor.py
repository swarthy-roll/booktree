from dataclasses import dataclass
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