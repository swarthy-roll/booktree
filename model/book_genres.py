from peewee import ForeignKeyField, CompositeKey
from model import book, category, base_model as bm

class Book_Genres(bm.Base_Model):
    book = ForeignKeyField(book.Book, backref='book_genres')
    genres = ForeignKeyField(category.Category, backref='genre_books')

    class Meta:
        primary_key = CompositeKey('book', 'genres')