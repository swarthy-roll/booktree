from peewee import CharField, DateTimeField
from datetime import datetime
from model.base_model import Base_Model

class Contributor(Base_Model):
    name = CharField(unique=True)
    timestamp = DateTimeField(default = datetime.now)