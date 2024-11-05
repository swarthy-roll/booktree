from dataclasses import dataclass
from model.category import Category as Categories_Model
from utils.utils import to_camel_case

@dataclass
class Categories:
    name:str=""

    def set_name(self, name):
        if name:
            self.name = to_camel_case(name)

    def save(self):
        category, result = Categories_Model.get_or_create(**self.__dict__)
        #log result when verbose
        return category