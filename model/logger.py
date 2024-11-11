from peewee import CharField, DateTimeField, TextField
from datetime import datetime
from model.base_model import Base_Model

class Logger(Base_Model):
    message = TextField()
    level = CharField(max_length=10)
    timestamp = DateTimeField(default = datetime.now)