from peewee import ForeignKeyField, CompositeKey
from model import book, contributor, base_model as bm

class Book_Narrator(bm.Base_Model):
    book = ForeignKeyField(book.Book, backref='book_narrator')
    narrator = ForeignKeyField(contributor.Contributor, backref='narrator_books')

    class Meta:
        primary_key = CompositeKey('book', 'narrator')