import httpx
import re
from dataclasses import dataclass
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import myx_classes
import time
import search

@dataclass
class Goodreads:
    driver: webdriver
    is_signup_modal_dismissed: bool
    genre_limit: int = 2
    
    def __init__(self):
        self.driver=self.start_webdriver(True)
        self.is_signup_modal_dismissed = False

    def fetch_all(self, book, isbn="", title="", author=""):
        try:
            # instantiate our search class and search for the book url
            url = search.Search()
            url.search(isbn, title, author)

            if url.book_url:
                # get the HTML for the book page
                page = self.get_book_page_content(url.book_url, self.driver)

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

    def start_webdriver(self, headless):
        try:    
            options = Options()
            if headless:
                options.add_argument("--headless=new")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36")

            # Initialize the WebDriver
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=options)

            return driver
        
        except Exception as e:
            print(f"Error occurred while instantiating webdriver {e}")

    def stop_webdriver(self, driver):
        try:
            driver.quit()
        except Exception as e:
            print(f"An error occurred while quitting the webdriver service {e}")

    def search_goodreads(self, isbn="",title="",author=""):

        if len(isbn) > 0:
            search_url = f"{self.goodreads_search_url}{isbn}"
            # A goodreads search for the ISBN redirects directly to the book page. So if the ISBN is known, scraping for the URL is unnecesary.
            return search_url
        else:
            search_url = f"{self.goodreads_search_url}{title} {author}"

        try:
            response = httpx.get(search_url, headers=self.headers)
            response.raise_for_status()

            # Parse the book page HTML
            search = BeautifulSoup(response.content, "html.parser")
            top_book = search.find("a", class_="bookTitle")

            if top_book:
                # Return the first item in the search results and clean up the URL by stripping off all params
                return self.goodreads_url + top_book["href"].split('?')[0]
            
        except httpx.HTTPStatusError as e:
            print(f"An error occurred: the server returned a {e.response.status_code} code")
        except Exception as e:
            print(f"Goodreads search {search_url} returned zero results.")

    def click_button(self, driver, xpath, wait, sleep=0, scroll=False):
        try:
            button = WebDriverWait(driver, wait).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            if button:
                if scroll:
                    actions = ActionChains(driver)
                    actions.move_to_element(button).perform()  
                button.click()
                time.sleep(sleep)
        except Exception as e:
            print(f"Error interacting with button {xpath}. Usually this means the button isn't present to be interacted with.")

    def get_book_page_content(self, book_url, driver):
        # Book pages unfortunately do not initially load all the metadata we require.
        # Before we parse the page HTML, we must click a few buttons to load all the metadata.
        
        try:
            driver.get(book_url)
            
            # Dismiss the sign-in modal. If this is present at all, dismissing it should dismiss it for the duration of scraping session
            if self.is_signup_modal_dismissed is False:
                self.click_button(driver, xpath="//button[@aria-label='Close']", wait=3)
                self.is_signup_modal_dismissed = True

            # Click "...more" button
            self.click_button(driver, xpath="//button[@aria-label='Show all items in the list']", wait=3, sleep=1)

            # Click "Book details & editions" button
            self.click_button(driver, xpath="//button[@aria-label='Book details and editions']", wait=3, sleep=1, scroll=True)

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