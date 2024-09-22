import httpx
import re
from dataclasses import dataclass, field
from bs4 import BeautifulSoup

@dataclass
class Search:
    headers: dict = field(default_factory=lambda: {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"})
    search_engines: dict = field(default_factory=lambda: {"goodreads": "https://www.goodreads.com","google": "https://www.google.com"})
    base_url: str = ""
    engine: str = ""
    search_endpoint: str = "/search?q="
    href_to_match: str = "/book/show/"
    google_param: str = "url="
    isbn13_pattern: str = r'^\d{13}$'
    google_site_prefix: str = "site:"
    book_url: str = ""

    def __post_init__(self):
        self.base_url = f"{self.search_engines.get(self.engine)}{self.search_endpoint}"

    def set_engine(self, isbn="", title="", author=""):
        if isbn:
            self.engine = "goodreads"
        elif title and author:
            self.engine = "google"
        else:
            self.engine = "goodreads"
    
    def search(self, isbn="", title="", author=""):
        # the goal is to return a Goodreads URL for the book being searched for
        # if an ISBN is passed to Goodreads, Goodreads will redirect to the book page automatically
        try:
            self.set_engine(isbn, title, author)
            if self.engine == "goodreads" and re.findall(self.isbn13_pattern,isbn):
                # if the engine is goodreads and the search string is ISBN, return the base URL + ISBN
                return f"{self.base_url}{isbn}"
            elif self.engine == "google":
                search_url = f"{self.base_url}{self.google_site_prefix}{self.search_engines.get("goodreads")} {title} {author}"
            else:
                # catch-all if only the title is available.
                search_url = f"{self.base_url}{title}"

            response = httpx.get(search_url, headers=self.headers)
            response.raise_for_status()

            # parse the resulting page of HTML that comprises the search page
            search_page = BeautifulSoup(response.content, "html.parser")

            if search_page:
                if self.engine == "google":
                    self.set_google_book_url(search_page)
                else:
                    self.set_goodreads_book_url(search_page)

        except httpx.HTTPStatusError as e:
            print(f"ERROR: The {self.engine} server returned a {e.response.status_code} code. URL attemped: {search_url}.")
        except Exception as e:
            print(f"Search error with URL")

    def set_goodreads_book_url(self, page):
        # goodreads search results "a" tags all share the bookTitle class id, so we can choose the first result as the "best" result.
        
        try:
            result = page.find("a", class_="bookTitle")["href"].split('?')[0]
            
            if result:
                self.book_url = f"{self.search_engines.get(self.engine)}{result}"
        except Exception as e:
            print(f"ERROR: couldn't parse the goodreads search page HTML")

    def set_google_book_url(self, page):
        # the goal is to find all "a" tags on the page and filter them down to the first one that contains the href match string (href_to_match).
        # the href value is pulled from the resulting "a" tag, and then the value is split by "&" into the various parameter blocks, which is then iterated over.
        # each block is evaluated until the google_param is found. the parameter name is stripped of the block, leaving only the URL.
        # the URL is returned to the caller

        try:
            for part in page.find('a', href=lambda href: href and self.href_to_match in href)["href"].split("&"):
                if self.google_param in part:
                    self.book_url = part.removeprefix(self.google_param)
        except Exception as e:
            print(f"ERROR: couldn't parse the google HTML")
