from peewee import SqliteDatabase

# SQLite database connection
db = SqliteDatabase('book.db', pragmas={'foreign_keys': 1})