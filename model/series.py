from peewee import CharField
from model.base_model import Base_Model

class Series(Base_Model):
    name = CharField()
    part = CharField()
    separator = CharField()