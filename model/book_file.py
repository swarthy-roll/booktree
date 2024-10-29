from peewee import ForeignKeyField, CompositeKey
from model import book as Book, base_model as bm, file as File

class Book_File(bm.Base_Model):
    book = ForeignKeyField(Book.Book, backref='book_files')
    file = ForeignKeyField(File.File, backref='file_books', on_delete='CASCADE') # cascade option: if the file is deleted from the db, delete any books associated with it

    class Meta:
        primary_key = CompositeKey('book', 'file')