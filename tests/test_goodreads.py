import pytest
from utils.goodreads import Goodreads
from utils.config import Config
from entities.book import Book

def test_goodreads_instantiation():
    goodreads = Goodreads()
    assert goodreads is not None
    assert goodreads.config is not None
    assert goodreads.crawler is not None
    assert goodreads.logger is not None

    goodreads = Goodreads(Config())
    assert goodreads is not None
    assert goodreads.config is not None
    assert goodreads.crawler is not None
    assert goodreads.logger is not None

@pytest.mark.parametrize("isbn, title, authors, expected", [
    ("9781250175571", "The Memory of Souls (A chorus of Dragons 3)", "Lyons, Jenn", {"title": "The Memory of Souls", 
                                                                                     "subtitle": None,
                                                                                     "authors": "Jenn Lyons", 
                                                                                     "tags": 9, # ten on the page, minus one (audiobook)
                                                                                     "publication_year": "2020", 
                                                                                     "isbn": "9781250175571",
                                                                                     "publisher": "Tor Books",
                                                                                     "book_cover_url": "https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1571058946i/52378515.jpg"
                                                                                     }),
    #("value3", "value4", "value5", "result2"),
])
def test_goodreads_fetch_all(isbn, title, authors, expected):
    goodreads = Goodreads()
    book = goodreads.fetch_all(Book(source=2), isbn, title, authors)

    assert book is not None
    assert book.title == expected.get("title")
    assert book.subtitle == expected.get("subtitle")
    assert len(book.tags) == expected.get("tags")
    assert book.publication_year == expected.get("publication_year")
    assert book.isbn == expected.get("isbn")
    assert book.publisher == expected.get("publisher")
    assert book.book_cover_url == expected.get("book_cover_url")
