from peewee import Model
from database.database import db

class Base_Model(Model):
    @classmethod
    def record_exists(cls, key, value):
        return cls.select().where(getattr(cls, key) == value).exists()
    class Meta:
        database = db
