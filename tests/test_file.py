from entities.file import File
from entities.book import Book
from entities.contributor import Contributor
from entities.series import Series
from utils.config import Config
from pathlib import Path


def test_file_book_reorder_by_preference():
    config = Config()
    file = File(r'C:\Users\Aaron\Documents\ebooks\Costanza Casati - Clytemnestra.epub', config)
    
    file.book.append(Book(1))
    file.book.append(Book(2))
    file.book.append(Book(3))
    file.book.append(Book(4))

    file.sort_books_by_preference()
    order = config.get_metadata_preference()

    assert file.full_path is not None
    for i in range(4):
        assert file.book[i].source == order[i]

def test_file_set_media_path():
    title = 'Clytemnestra'
    author1 = 'Costanza Casati'
    author2 = 'Example Author'
    series_name = 'Example'
    series_part = '1'
    config = Config()
    file = File(r'C:\Users\Aaron\Documents\ebooks\Costanza Casati - Clytemnestra.epub', config)
    file.book.append(Book(1)) # embedded book source
    file.book.append(Book(4)) # mama book source

    file.book[0].title = title
    file.book[0].authors.append(Contributor(author1))
    file.book[0].authors.append(Contributor(author2)) # a second author is added to test that the first author is the only one returned

    file.book[1].title = title
    file.book[1].series = Series(series_name, series_part) # series is only added on the second instance to test that the books are correctly coalesced

    file.sort_books_by_preference()

    tokens = file.get_tokens_by_preference()

    assert tokens.get('title') == title
    assert tokens.get('author') == author1
    assert tokens.get('series') == series_name
    assert tokens.get('part') == series_part

    file.set_media_path()

    assert file.media_path
    assert Path(file.media_path).resolve