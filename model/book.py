from peewee import BooleanField, CharField, FloatField, IntegerField, TextField
from model import base_model as bm

class Book(bm.Base_Model):
    asin = CharField(null=True)
    isbn = CharField(null=True)
    title = CharField()
    subtitle = CharField(null=True)
    publication_year = CharField(null=True)
    publication_name = CharField(null=True)
    publisher = CharField(null=True)
    length = IntegerField(default=0)
    duration = FloatField(default=0.0)
    matchRate = FloatField(default=0.0)
    language = CharField(default="English")
    snatched = BooleanField(default=False)
    description = TextField(null=True)
    source = IntegerField()