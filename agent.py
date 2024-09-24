import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains

class Agent:
    driver: webdriver
    headless: bool

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.start_webdriver()

    def start_webdriver(self):
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
        
        except Exception as e:
            print(f"Error occurred while instantiating webdriver {e}")

    def stop_webdriver(self):
        try:
            self.driver.quit()
        except Exception as e:
            print(f"An error occurred while quitting the webdriver service {e}")

    def click_button(self, xpath, wait, sleep=0, scroll=False):
        try:
            button = WebDriverWait(self.driver, wait).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            if button:
                if scroll:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(button).perform() 
                button.click()
                time.sleep(sleep)
        except Exception as e:
            print(f"Error interacting with button {xpath}. Usually this means the button isn't present to be interacted with.")