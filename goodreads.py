import re
from dataclasses import dataclass
from bs4 import BeautifulSoup
import myx_classes
import time
import search
import agent

@dataclass
class Goodreads:
    crawler: agent.Agent
    genre_limit: int = 2
    xpath_close: str = "//button[@aria-label='Close']"
    xpath_show_all: str = "//button[@aria-label='Show all items in the list']"
    xpath_book_details: str = "//button[@aria-label='Book details and editions']"
    
    def __init__(self):
        self.crawler=agent.Agent(headless=True)

    def fetch_all(self, book, isbn="", title="", author=""):
        try:
            # instantiate our search class and search for the book url
            url = search.Search()
            url.search(self.crawler.driver, isbn, title, author)

            if url.book_url:
                # get the HTML for the book page
                page = self.get_book_page_content(url.book_url)

                if page:
                    # parse for the original publication year
                    book.publication_year = self.get_original_publication_year(page)

                    # parse for the description
                    book.description = self.get_description(page)

                    # parse for the genres. the get_genres method returns a list, so we convert the list into a CSV string
                    categories = ','.join(self.get_genres(page))

                    # use the categories data to set the genres
                    book.setGenres(categories)

                    # use the categories data to set the tags
                    book.setTags(categories)

                    # parse for the series
                    series = self.get_series(page)
                    
                    book.series.clear()
                    if series:
                        for name, part in series.items():
                            book.series.append(myx_classes.Series(name, part))

                    # parse for the publisher
                    book.publisher = self.get_publisher(page)

                    # parse for the ISBN
                    book.isbn = self.get_isbn(page)

                return book
        except Exception as e:
            print("Encountered an issue fetching Goodreads metadata")

    def get_book_page_content(self, book_url):
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
            return BeautifulSoup(driver.page_source, "html.parser")
        except Exception as e:
            print(f"An unexpected error occurred while getting the book page content: {e}")

    def get_genres(self, page_content):
        try:
            # Find the div containing the genres using the data-testid attribute
            genres_div = page_content.find("div", {"data-testid": "genresList"})
            
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

    def get_original_publication_year(self, page_content):
        pattern = r'\b\d{4}\b'
        
        try:
            pub_date_div = page_content.find("div", class_="BookDetails")

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

    def get_description(self, page_content):
        try:
            descr_div = page_content.find("div", {"data-testid": "description"})

            if descr_div:
                descr_span = descr_div.find("span", class_="Formatted")
                if descr_span:
                    return descr_span.get_text("\n\n",strip=True)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")    

    def get_series(self, page_content):
        series_dict = {}

        try:
            div = self.get_div_by_dt(page_content, "Series")
            
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

    def get_div_by_dt(self, page_content, label):
        try:
            book_details = page_content.find("div", {"class": "BookDetails"})

            # Search for divs within Book Details with the class DescListItem.
            # There are several of these, so use the label of the data section as a filter
            # Iterate over all the divs until one is found that contains the proper label
            all_divs = book_details.find_all("div", class_='DescListItem')
            for div in all_divs:
                if div.find_next("dt").get_text(strip=True) == label:
                    return div

        except Exception as e:
            print(f"Could not find {label} on the page")  

    def get_publisher(self, page_content):
        try:
            div = self.get_div_by_dt(page_content, "Published").find("div", {"data-testid": "contentContainer"})
            if div and "by" in div.next_element:
                return div.next_element.split("by")[-1].strip()
            else:
                return ""
        except Exception as e:
            print(f"There is no publisher attribute on this page")    

    def get_isbn(self, page_content):
        try:
            div = self.get_div_by_dt(page_content, "ISBN").find("div", {"data-testid": "contentContainer"})
            if div:
                isbn = div.next_element.strip(' ')
                return isbn
            else: return ""
        except Exception as e:
            print(f"There is no ISBN attribute on this page")    