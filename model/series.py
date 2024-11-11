from peewee import CharField, DateTimeField
from datetime import datetime
from model.base_model import Base_Model

class Series(Base_Model):
    name = CharField(unique=True)
    part = CharField()
    separator = CharField()
    timestamp = DateTimeField(default = datetime.now)