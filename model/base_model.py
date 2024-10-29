from peewee import Model
from database.database import db

class Base_Model(Model):
    class Meta:
        database = db