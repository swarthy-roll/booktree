import re, time, random, traceback
from dataclasses import dataclass
from bs4 import BeautifulSoup
from utils.search import Search
from utils.agent import Agent
from utils.config import Config
from entities.series import Series
from entities.book import Book
from entities.logger import Logger

@dataclass
class Goodreads:
    crawler: Agent
    config: Config
    page_content: BeautifulSoup
    logger:Logger
    book_url:str
    genre_limit: int = 2
    xpath_close: str = "//button[@aria-label='Close']"
    xpath_show_all: str = "//button[@aria-label='Show all items in the list']"
    xpath_book_details: str = "//button[@aria-label='Book details and editions']"
    
    def __init__(self, config:Config = None):
        if not config:
            config = Config()
        self.config = config
        self.crawler = Agent(headless=config.headless_mode)
        self.logger = Logger()

    def fetch_all(self, book:Book, isbn="", title="", author=""):
        self.logger.log('DEBUG', f'Beginning Goodreads scrape: ISBN={isbn}, title={title}, author={author}')
        try:
            # bot detection mitigation effort...
            # if ISBN is known, the Goodreads page can be accessed directly, so there's no need to avoid Google bot detection
            if not isbn:
                wait = random.randint(30, 56)
                self.logger.log('INFO',f'Execution paused for {wait} seconds as a bot detection mitigation effort...')
                time.sleep(wait)
            
            # instantiate our search class and search for the book url
            url = Search()
            url.search(self.crawler.driver, isbn, title, author)
            self.book_url = url.book_url

            if url.book_url:
                self.logger.log('DEBUG',f'Goodreads book URL: {url.book_url}')
                
                # set the HTML for the book page
                self.set_page_content(url.book_url)

                if self.page_content:
                    # store the main content portion of the page for reference and possible re-parsing
                    main_content = self.page_content.find('div', class_='BookPage__mainContent')
                    if main_content:
                        book.raw_source = str(main_content)
                    
                    # parse for the title/subtitle
                    book.set_title(self.get_title())

                    # parse for the author(s)
                    book.set_authors(','.join(self.get_contributors()))
                    
                    # parse for the original publication year
                    book.publication_year = self.get_original_publication_year()

                    # parse for the book cover url
                    book.book_cover_url = self.get_book_cover()

                    # parse for the description
                    book.description = self.get_description()

                    # parse for the genres. the get_genres method returns a list, so we convert the list into a CSV string
                    categories = ','.join(self.get_genres())

                    # use the categories data to set the genres
                    book.set_genres(categories)

                    # use the categories data to set the tags
                    book.set_tags(categories)

                    # parse for the series
                    series = self.get_series()
                    
                    book.series.clear()
                    if series:
                        for name, part in series.items():
                            book.series.append(Series(name, part))

                    # parse for the publisher
                    book.publisher = self.get_publisher()

                    # parse for the ISBN
                    book.isbn = self.get_isbn()

                return book
        except Exception:
            self.logger.log('ERROR',f'Encountered an issue fetching Goodreads metadata: {traceback.format_exc()}')
            return None

    def set_page_content(self, book_url):
        # Book pages unfortunately do not initially load all the metadata we require.
        # Before we parse the page HTML, we must click a few buttons to load all the metadata.
        driver = self.crawler.driver

        try:
            driver.get(book_url)
            
            attempt = 0 
            close_result = False
            show_all_result = False
            book_details_result = False

            # sometimes the page won't load very quickly or other shenanigans occur and cause the button clicks to misfire
            # this goes through three retries before abandoning
            while not show_all_result and not book_details_result and attempt < 3:
                #if not close_result:
                # Dismiss the sign-in modal
                self.crawler.click_button(xpath=self.xpath_close, wait=3)

                if not show_all_result:
                    # Click "...more" button
                    show_all_result = self.crawler.click_button(xpath=self.xpath_show_all, wait=3, sleep=1)
                    
                if not book_details_result:
                    # Click "Book details & editions" button
                    book_details_result = self.crawler.click_button(xpath=self.xpath_book_details, wait=3, sleep=1, scroll=True)

                if show_all_result and book_details_result:
                    break
                
                attempt += 1
                self.logger.log('DEBUG', f'Attempt to click one or more buttons failed. Retry {attempt} of 3.')

            # Use beautifulsoup to parse the HTML and return that to the caller
            self.page_content = BeautifulSoup(driver.page_source, "html.parser")
        except Exception:
            self.logger.log('ERROR', f'An unexpected error occurred while getting the book page content for {self.book_url}: {traceback.format_exc()}')

    def get_genres(self):
        self.logger.log('DEBUG', f'Scraping genres on {self.book_url}...')
        try:
            # Find the div containing the genres using the data-testid attribute
            genres_div = self.page_content.find("div", {"data-testid": "genresList"})
            
            if genres_div:
                # Find all the span elements with the class "Button__labelItem" inside the genres div
                genre_spans = genres_div.find_all("span", class_="Button__labelItem")

                if genre_spans:
                    genres = []
                    for genre in genre_spans:
                        genre_text = genre.get_text(strip=True)
                        
                        if genre_text not in {'...more', '...show all', 'Audiobook'}:
                            genres.append(genre_text)
                    return genres
                else:
                    self.logger.log('DEBUG', f'No genres found within the genres section of {self.book_url}.')
            else:
                self.logger.log('DEBUG', f'Genres section not found on {self.book_url}.')
        except Exception:
            self.logger.log('ERROR', f'An unexpected error occurred while getting genres: {traceback.format_exc()}')

    def get_contributors(self):
        self.logger.log('DEBUG', f'Scraping contributors on {self.book_url}...')
        try:
            contributor_div = self.page_content.find("div", class_="ContributorLinksList")
            if contributor_div:
                name_spans = contributor_div.find_all("span", {"data-testid": "name"})
                if name_spans:
                    names = []
                    for name in name_spans:
                        names.append(name.get_text(strip=True))
                    return names

        except Exception:
            self.logger.log('ERROR', f'An unexpected error occurred while getting contributors on {self.book_url}: {traceback.format_exc()}')

    def get_original_publication_year(self):
        self.logger.log('DEBUG', f'Scraping publication year on {self.book_url}...')
        pattern = r'\b\d{4}\b'
        
        try:
            pub_date_div = self.page_content.find("div", class_="BookDetails")

            if pub_date_div:
                pub_date = pub_date_div.find("p", {"data-testid": "publicationInfo"})

            if pub_date:
                # The string returned will look something like 'First Published January 1, 1899'. 
                # Use regex to parse the string and return the year.
                year = re.findall(pattern,pub_date.get_text(strip=True))
                
                #findall returns an array even though in this case there's one result. access the first/only result using [0]
                return year[0] 
            
        except Exception:
            self.logger.log('ERROR', f'An unexpected error occurred while getting the publication year on {self.book_url}: {traceback.format_exc()}')

    def get_book_cover(self):
        self.logger.log('DEBUG', f'Scraping book cover URL on {self.book_url}...')
        try:
            cover_div = self.page_content.find("div", class_="BookCover__image")
            if cover_div:
                cover = cover_div.find("img", class_="ResponsiveImage")
                if cover:
                    return cover.get('src')
        except Exception:
            self.logger.log('ERROR', f'An unexpected error occurred while getting the book cover on {self.book_url}: {traceback.format_exc()}')

    def get_title(self):
        self.logger.log('DEBUG', f'Scraping title on {self.book_url}...')
        try:
            title_div = self.page_content.find("div", class_="BookPageTitleSection__title")
            if title_div:
                title = title_div.find("h1", {"data-testid": "bookTitle"})
                if title:
                    return title.get_text(strip=True)
        except Exception:
            self.logger.log('ERROR', f'An unexpected error occurred while getting the book title on {self.book_url}: {traceback.format_exc()}')

    def get_description(self):
        self.logger.log('DEBUG', f'Scraping description on {self.book_url}...')
        try:
            descr_div = self.page_content.find("div", {"data-testid": "description"})

            if descr_div:
                descr_span = descr_div.find("span", class_="Formatted")
                if descr_span:
                    return descr_span.get_text("\n\n",strip=True)
        except Exception:
            self.logger.log('ERROR', f'An unexpected error occurred while getting the book description on {self.book_url}: {traceback.format_exc()}')

    def get_series(self):
        self.logger.log('DEBUG', f'Scraping series details on {self.book_url}...')
        series_dict = {}

        try:
            div = self.get_div_by_dt("Series")
            
            if div:
                # Iterate through all the "a" tags, parsing out the tag text and the number associated with it
                for series in div.find_all("a"):
                    text = series.get_text(strip=True)
                    number = series.find_next_sibling(string=True)
                    if number:
                        number = number.strip('(#,) ')
                        series_dict[text] = number
                    else:
                        series_dict[text] = ''

            return series_dict
        except Exception:
            self.logger.log('ERROR', f'An unexpected error occurred while getting the series on {self.book_url}: {traceback.format_exc()}')    

    def get_div_by_dt(self, label):
        try:
            book_details = self.page_content.find("div", {"class": "BookDetails"})

            # Search for divs within Book Details with the class DescListItem.
            # There are several of these, so use the label of the data section as a filter
            # Iterate over all the divs until one is found that contains the proper label
            if book_details:
                all_divs = book_details.find_all("div", class_='DescListItem')
                for div in all_divs:
                    if div.find_next("dt").get_text(strip=True) == label:
                        return div

        except Exception:
            self.logger.log('ERROR', f'Could not find {label} on the page {self.book_url}: {traceback.format_exc()}')

    def get_publisher(self):
        self.logger.log('DEBUG', f'Scraping publisher on {self.book_url}...')
        try:
            div = self.get_div_by_dt("Published")
            if div:
                div = div.find("div", {"data-testid": "contentContainer"})
                if div and "by" in div.next_element:
                    return div.next_element.split("by")[-1].strip()
            return ""
        except Exception:
            self.logger.log('ERROR', f'An unexpected error occurred while getting the book publisher on {self.book_url}: {traceback.format_exc()}')  

    def get_isbn(self):
        self.logger.log('DEBUG', f'Scraping ISBN on {self.book_url}...')
        try:
            div = self.get_div_by_dt("ISBN")
            if div: 
                div = div.find("div", {"data-testid": "contentContainer"})
                if div:
                    isbn = div.next_element.strip(' ')
                    return isbn
            return ""
        except Exception:
            self.logger.log('ERROR', f'An unexpected error occurred while getting the ISBN on {self.book_url}: {traceback.format_exc()}') 