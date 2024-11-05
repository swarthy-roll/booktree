from dataclasses import dataclass
from model.series import Series as Series_Model

@dataclass
class Series:
    name:str=""
    part:str=""
    separator:str=""
    
    def save(self):
        series, result = Series_Model.get_or_create(**self.__dict__)
        return series

    def getSeriesPart(self):
        if (len(self.part.strip()) > 0):
            return f"{self.name} {self.separator}{str(self.part)}"
        else:
            return self.name