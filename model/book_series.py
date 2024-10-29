from peewee import ForeignKeyField, CompositeKey
from model import book, series, base_model as bm

class Book_Series(bm.Base_Model):
    book = ForeignKeyField(book.Book, backref='book_series')
    series = ForeignKeyField(series.Series, backref='series_books')

    class Meta:
        primary_key = CompositeKey('book', 'series')