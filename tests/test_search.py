from utils.search import Search
from utils.agent import Agent

def test_search_instantiation():
    search = Search()
    assert search is not None

def test_search_set_engine():
    search = Search()

    search.set_engine(isbn="9780795316999", title="The Rise And Fall of the Third Reich", author="William L. Shirer")
    assert search.engine == 'goodreads'

    search.set_engine(isbn="", title="The Rise And Fall of the Third Reich", author="William L. Shirer")
    assert search.engine == 'google'

    search.set_engine(isbn="", title="The Rise And Fall of the Third Reich", author="")
    assert search.engine == 'goodreads'

def test_search():
    isbn = '9780795316999'
    title = 'The Rise And Fall of the Third Reich'
    author = 'William L. Shirer'
    search_result_url = 'https://www.goodreads.com/book/show/767171.The_Rise_and_Fall_of_the_Third_Reich'
    redirect_url = 'https://www.goodreads.com/search?q=9780795316999'
    agent = Agent(True)
    search = Search()

    search.search(agent.driver, isbn=isbn)
    assert search.book_url == redirect_url

    search.search(agent.driver, title=title, author=author)
    assert search.book_url == search_result_url

    search.search(agent.driver, title=title)
    assert search.book_url == search_result_url