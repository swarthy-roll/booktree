from peewee import ForeignKeyField, CompositeKey
from model import book, contributor, base_model as bm

class Book_Author(bm.Base_Model):
    book = ForeignKeyField(book.Book, backref='book_authors')
    author = ForeignKeyField(contributor.Contributor, backref='author_books')

    class Meta:
        primary_key = CompositeKey('book', 'author')