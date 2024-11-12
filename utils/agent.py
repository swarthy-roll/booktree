import time, traceback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from entities.logger import Logger

class Agent:
    driver: webdriver
    headless: bool
    logger: Logger

    def __new__(cls, *args, **kwargs):
        if getattr(cls, "_instance", None) is None:
            cls._instance = super(Agent, cls).__new__(cls)
        return cls._instance

    def __init__(self, headless: bool = True):
        if Agent._instance is self:
            self.logger = Logger()
            self.logger.log('DEBUG',f'Initializing the scraper Agent...')
            self.headless = headless
            self.start_webdriver()

    def start_webdriver(self):
        self.logger.log('DEBUG',f'Starting webdriver in headless = {self.headless} mode.')
        try:    
            options = Options()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36")
            options.add_argument("--disk-cache-size=4096") # this option should help performance by caching common stuffs

            # Initialize the WebDriver
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=options)
        
        except Exception:
            self.logger.log('ERROR',f'Error occurred while instantiating webdriver: {traceback.format_exc()}')

    def stop_webdriver(self):
        try:
            self.driver.quit()
        except Exception:
            self.logger.log('ERROR',f'An error occurred while quitting the webdriver service: {traceback.format_exc()}')

    def click_button(self, xpath, wait, sleep=0, scroll=False):
        try:
            self.logger.log('DEBUG',f'Attempting to click button: {xpath}...')
            button = WebDriverWait(self.driver, wait).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            if button:
                if scroll:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(button).perform() 
                button.click()
                time.sleep(sleep)
                return True
        except Exception:
            self.logger.log('WARNING',f"Error interacting with button {xpath}. Usually this means the button isn't present to be interacted with.")
            return False