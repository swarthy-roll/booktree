from peewee import BooleanField, CharField, FloatField, IntegerField, TextField, DateTimeField
from datetime import datetime
from model import base_model as bm

class Book(bm.Base_Model):
    asin = CharField(null=True)
    isbn = CharField(null=True)
    title = CharField()
    subtitle = CharField(null=True)
    publication_year = CharField(null=True)
    publisher = CharField(null=True)
    length = IntegerField(default=0)
    duration = FloatField(default=0.0)
    match_rate = FloatField(default=0.0)
    language = CharField(null=True)
    snatched = BooleanField(default=False)
    description = TextField(null=True)
    raw_source = TextField(null=True)
    book_cover_url = CharField(null=True)
    source = IntegerField()
    timestamp = DateTimeField(default = datetime.now)