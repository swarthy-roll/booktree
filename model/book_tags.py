from peewee import ForeignKeyField, CompositeKey
from model import book, category, base_model as bm

class Book_Tags(bm.Base_Model):
    book = ForeignKeyField(book.Book, backref='book_tags')
    tags = ForeignKeyField(category.Category, backref='tag_books')

    class Meta:
        primary_key = CompositeKey('book', 'tags')