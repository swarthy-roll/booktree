from dataclasses import dataclass

@dataclass
class Series:
    name:str=""
    part:str=""
    separator:str=""
    
    def getSeriesPart(self):
        if (len(self.part.strip()) > 0):
            return f"{self.name} {self.separator}{str(self.part)}"
        else:
            return self.name