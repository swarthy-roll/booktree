from peewee import CharField
from model.base_model import Base_Model

class Contributor(Base_Model):
    name = CharField()