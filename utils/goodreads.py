import re, time, random
from dataclasses import dataclass
from bs4 import BeautifulSoup
from utils.search import Search
from utils.agent import Agent
from entities.series import Series
from entities.book import Book

@dataclass
class Goodreads:
    crawler: Agent
    page_content: BeautifulSoup
    genre_limit: int = 2
    xpath_close: str = "//button[@aria-label='Close']"
    xpath_show_all: str = "//button[@aria-label='Show all items in the list']"
    xpath_book_details: str = "//button[@aria-label='Book details and editions']"
    
    def __init__(self):
        self.crawler=Agent(headless=True)

    def fetch_all(self, book:Book, isbn="", title="", author=""):
        try:
            # bot detection mitigation effort...
            # if ISBN is known, the Goodreads page can be accessed directly, so there's no need to avoid Google bot detection
            if not isbn:
                time.sleep(random.randint(30, 56))
            
            # instantiate our search class and search for the book url
            url = Search()
            url.search(self.crawler.driver, isbn, title, author)

            if url.book_url:
                # set the HTML for the book page
                self.set_page_content(url.book_url)

                if self.page_content:
                    # parse for the title/subtitle
                    book.set_title(self.get_title())

                    # parse for the author(s)
                    book.set_authors(','.join(self.get_contributors()))
                    
                    # parse for the original publication year
                    book.publication_year = self.get_original_publication_year()

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
        except Exception as e:
            print(f"Encountered an issue fetching Goodreads metadata: {e}")

    def set_page_content(self, book_url):
        # Book pages unfortunately do not initially load all the metadata we require.
        # Before we parse the page HTML, we must click a few buttons to load all the metadata.
        driver = self.crawler.driver

        try:
            driver.get(book_url)
            
            # Dismiss the sign-in modal
            self.crawler.click_button(xpath=self.xpath_close, wait=3)

            # Click "...more" button
            self.crawler.click_button(xpath=self.xpath_show_all, wait=3, sleep=1)

            # Click "Book details & editions" button
            self.crawler.click_button(xpath=self.xpath_book_details, wait=3, sleep=1, scroll=True)

            # Use beautifulsoup to parse the HTML and return that to the caller
            self.page_content = BeautifulSoup(driver.page_source, "html.parser")
        except Exception as e:
            print(f"An unexpected error occurred while getting the book page content: {e}")

    def get_genres(self):
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
                    print("No genres found within the genres section.")
            else:
                print("Genres section not found on this page.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def get_contributors(self):
        try:
            contributor_div = self.page_content.find("div", class_="ContributorLinksList")
            if contributor_div:
                name_spans = contributor_div.find_all("span", {"data-testid": "name"})
                if name_spans:
                    names = []
                    for name in name_spans:
                        names.append(name.get_text(strip=True))
                    return names

        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def get_original_publication_year(self):
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
            
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def get_title(self):
        try:
            title_div = self.page_content.find("div", class_="BookPageTitleSection__title")
            if title_div:
                title = title_div.find("h1", {"data-testid": "bookTitle"})
                if title:
                    return title.get_text(strip=True)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def get_description(self):
        try:
            descr_div = self.page_content.find("div", {"data-testid": "description"})

            if descr_div:
                descr_span = descr_div.find("span", class_="Formatted")
                if descr_span:
                    return descr_span.get_text("\n\n",strip=True)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")    

    def get_series(self):
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
        except Exception as e:
            print(f"An unexpected error occurred: {e}")          

    def get_div_by_dt(self, label):
        try:
            book_details = self.page_content.find("div", {"class": "BookDetails"})

            # Search for divs within Book Details with the class DescListItem.
            # There are several of these, so use the label of the data section as a filter
            # Iterate over all the divs until one is found that contains the proper label
            all_divs = book_details.find_all("div", class_='DescListItem')
            for div in all_divs:
                if div.find_next("dt").get_text(strip=True) == label:
                    return div

        except Exception as e:
            print(f"Could not find {label} on the page")  

    def get_publisher(self):
        try:
            div = self.get_div_by_dt("Published").find("div", {"data-testid": "contentContainer"})
            if div and "by" in div.next_element:
                return div.next_element.split("by")[-1].strip()
            else:
                return ""
        except Exception as e:
            print(f"There is no publisher attribute on this page")    

    def get_isbn(self):
        try:
            div = self.get_div_by_dt("ISBN").find("div", {"data-testid": "contentContainer"})
            if div:
                isbn = div.next_element.strip(' ')
                return isbn
            else: return ""
        except Exception as e:
            print(f"There is no ISBN attribute on this page")    