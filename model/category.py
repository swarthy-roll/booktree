from peewee import CharField
from model.base_model import Base_Model

class Category(Base_Model):
    name = CharField()