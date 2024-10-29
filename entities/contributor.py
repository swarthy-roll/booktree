from dataclasses import dataclass

@dataclass
class Contributor:
    name:str

    def removeGA (author:str):
        #remove Graphic Audio and special characters like ()[]
        cleanAuthor = author.replace("GraphicAudio","").replace("[","").replace("]","")
        return cleanAuthor.strip()