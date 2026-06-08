import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# --- SELECTOR CONFIGURATION ---
# These selectors are based on the current VTU Internyet portal layout.
SELECTORS = {
    "login_email": 'input[placeholder*="email"]',
    "login_password": 'input#password',
    "login_button": 'button[type="submit"]',
    "internship_dropdown": "button#internship_id",
    "internship_option": "//div[@role='option']//span[contains(text(), 'Android App Development')]",
    "date_picker_btn": "//button[contains(span/text(), 'Pick a Date') or contains(text(), 'Pick a Date') or contains(@class, 'calendar')]",
    "continue_btn": "//button[normalize-space()='Continue']",
}

class VTUDiaryChecker:
    def __init__(self):
        self.missing_dates = []
        self.setup_driver()
        self.wait = WebDriverWait(self.driver, 30)

    def setup_driver(self):
        """Initializes the Chrome WebDriver."""
        chrome_options = Options()
        # comment the line below to run in head mode (browser window will be visible)
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)

    def login(self, email, password, retries=3):
        """Handles the login process with retries."""
        for attempt in range(retries):
            try:
                print(f"[#] Login attempt {attempt + 1} of {retries}...")
                
                # Check if driver is still alive
                try:
                    self.driver.current_url
                except:
                    print("[!] Driver session lost, recreating...")
                    self.setup_driver()

                self.driver.get("https://vtu.internyet.in/sign-in")
                
                # Check if we are stuck on loading
                try:
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS["login_email"])))
                except TimeoutException:
                    print("[!] Login form not appearing, reloading...")
                    self.driver.refresh()
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS["login_email"])))

                print("[#] Entering credentials...")
                email_field = self.driver.find_element(By.CSS_SELECTOR, SELECTORS["login_email"])
                email_field.clear()
                email_field.send_keys(email)
                
                pass_field = self.driver.find_element(By.CSS_SELECTOR, SELECTORS["login_password"])
                pass_field.clear()
                pass_field.send_keys(password)
                
                print("[#] Clicking Sign In...")
                self.driver.find_element(By.CSS_SELECTOR, SELECTORS["login_button"]).click()
                
                # Wait for login to complete
                print("[#] Waiting for dashboard (timeout 60s)...")
                dashboard_wait = WebDriverWait(self.driver, 60)
                dashboard_wait.until(EC.url_contains("/dashboard"))
                print("[+] Login Successful!")
                
                # Close the 'Important Notice' modal if it exists
                try:
                    time.sleep(3) # Wait for modal to pop up
                    modal_close = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'close')] | //*[name()='svg']/*[name()='path' and @d='M18 6L6 18M6 6l12 12']/../..")
                    if modal_close:
                        modal_close[0].click()
                        print("[#] Closed the 'Important Notice' modal.")
                except:
                    pass 
                return # Success!
                
            except Exception as e:
                print(f"[!] Login attempt {attempt + 1} failed: {e}")
                self.driver.save_screenshot(f"login_fail_attempt_{attempt + 1}.png")
                if attempt == retries - 1:
                    raise e
                time.sleep(5)
                print("[#] Retrying...")

    def navigate_to_internship(self):
        """Navigates directly to the student diary page."""
        try:
            print("[#] Navigating to Student Diary section...")
            time.sleep(2) # Small delay for dynamic loading
            self.driver.get("https://vtu.internyet.in/dashboard/student/student-diary")
            
            # Ensure the diary list is loaded
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Diary')]")))
            print("[+] Diary page loaded.")
        except Exception as e:
            print(f"[!] Error navigating to diary page: {e}")

    def select_date_in_calendar(self, date_obj):
        """Clicks the specific date in the calendar picker, handling month/year selection."""
        try:
            target_day = str(date_obj.day)
            target_month = date_obj.strftime("%B") # e.g. "February"
            target_year = str(date_obj.year) # e.g. "2026"
            
            print(f"    [#] Opening calendar for {target_month} {target_day}, {target_year}...")
            
            # Click the date picker button to open calendar
            self.wait.until(EC.element_to_be_clickable((By.XPATH, SELECTORS["date_picker_btn"]))).click()
            time.sleep(1.5)
            
            # Wait for calendar to be visible
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'rdp')] | //div[contains(@class, 'calendar')]")))
            
            # Try to use dropdowns if available (React Day Picker often has them)
            try:
                from selenium.webdriver.support.ui import Select
                
                # Select Year
                year_select_el = self.driver.find_elements(By.CSS_SELECTOR, "select.rdp-years_dropdown")
                if year_select_el:
                    Select(year_select_el[0]).select_by_visible_text(target_year)
                    time.sleep(0.5)
                
                # Select Month
                month_select_el = self.driver.find_elements(By.CSS_SELECTOR, "select.rdp-months_dropdown")
                if month_select_el:
                    try:
                        Select(month_select_el[0]).select_by_visible_text(target_month)
                    except:
                        # Try abbreviation
                        Select(month_select_el[0]).select_by_visible_text(target_month[:3])
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"    [!] Dropdown navigation failed, falling back to arrows: {e}")
                # Fallback to arrow navigation
                max_attempts = 48 # Increased to handle longer ranges
                for _ in range(max_attempts):
                    header_el = self.driver.find_element(By.XPATH, "//div[contains(@class, 'rdp-caption')] | //div[contains(@class, 'calendar-header')] | //h2 | //div[contains(@class, 'rdp-caption_label')]")
                    current_header = header_el.text.lower()
                    
                    if f"{target_month} {target_year}".lower() in current_header or f"{target_month[:3]} {target_year}".lower() in current_header:
                        break
                    
                    # Parse current header to decide direction
                    try:
                        # Extract year from header
                        import re
                        match = re.search(r'\d{4}', current_header)
                        if match:
                            current_year = int(match.group())
                            if current_year < int(target_year):
                                direction = "next"
                            elif current_year > int(target_year):
                                direction = "prev"
                            else:
                                # Year is correct, check month
                                months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
                                current_month_idx = -1
                                for i, m in enumerate(months):
                                    if m in current_header:
                                        current_month_idx = i
                                        break
                                target_month_idx = date_obj.month - 1
                                if current_month_idx < target_month_idx:
                                    direction = "next"
                                else:
                                    direction = "prev"
                        else:
                            direction = "prev" # Default
                    except:
                        direction = "prev" # Default

                    if direction == "next":
                        btn = self.driver.find_element(By.XPATH, "//button[@aria-label='Go to the Next Month'] | //button[contains(@class, 'rdp-nav_button_next')]")
                    else:
                        btn = self.driver.find_element(By.XPATH, "//button[@aria-label='Go to the Previous Month'] | //button[contains(@class, 'rdp-nav_button_previous')]")
                    
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)

            # Click the day
            # Use aria-label for more precision if possible, otherwise text
            day_xpath = f"//button[contains(@class, 'rdp-day') and not(contains(@class, 'rdp-day_outside')) and text()='{target_day}']"
            # Fallback for aria-label which often contains the full date
            aria_xpath = f"//button[contains(@aria-label, '{target_month}') and contains(@aria-label, '{target_day}') and contains(@aria-label, '{target_year}')]"
            
            try:
                day_btn = self.driver.find_element(By.XPATH, day_xpath)
            except:
                day_btn = self.driver.find_element(By.XPATH, aria_xpath)
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", day_btn)
            day_btn.click()
            time.sleep(1)
            print(f"    [+] Date {target_month} {target_day} selected.")
            
        except Exception as e:
            print(f"    [!] Error selecting date: {e}")
            self.driver.save_screenshot(f"date_error_{date_obj.strftime('%Y%m%d')}.png")
            raise e

    def process_entry(self, date_val):
        """Processes a single date entry."""
        date_str = date_val.strftime("%Y-%m-%d")
        print(f"[>] Checking Date: {date_str}")

        # Skip Sundays
        if date_val.day_name() == 'Sunday':
            return

        try:
            # 1. Select Internship
            self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SELECTORS["internship_dropdown"]))).click()
            time.sleep(1)
            self.wait.until(EC.element_to_be_clickable((By.XPATH, SELECTORS["internship_option"]))).click()
            
            # 2. Select Date
            self.select_date_in_calendar(date_val)
            
            # 3. Click Continue
            self.wait.until(EC.element_to_be_clickable((By.XPATH, SELECTORS["continue_btn"]))).click()
            time.sleep(3) # Wait for form to load

            # 4. Check if skills are filled
            container_xpath = "//label[contains(text(), 'Skills Used')]/following-sibling::div"
            try:
                # We'll just look for the remove buttons which exist when a chip is added
                remove_buttons = self.driver.find_elements(By.XPATH, f"{container_xpath}//*[contains(@class, 'remove')] | {container_xpath}//*[name()='svg' and contains(@class, 'cross')]")
                
                # Another check is to look for 'multiValue'
                existing_tags = self.driver.find_elements(By.XPATH, f"{container_xpath}//*[contains(@class, 'multiValue')]")
                
                if len(remove_buttons) > 0 or len(existing_tags) > 0:
                    # Skills are filled, so we do nothing
                    pass
                else:
                    # Skills are not filled
                    self.missing_dates.append(date_str)
            except Exception as e:
                 self.missing_dates.append(date_str)
                 print(f"    [!] Error checking skills for {date_str}: {e}")
            
            # Navigate back to list for next entry
            self.driver.get("https://vtu.internyet.in/dashboard/student/student-diary")
            
            # Wait for form/list to load
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Diary')] | //*[contains(text(), 'Android App Development')] | //button[@id='internship_id']")))

        except Exception as e:
            print(f"    [!] Failed to check {date_str}: {e}")
            self.driver.get("https://vtu.internyet.in/dashboard/student/student-diary") # Reset

    def run(self, email, password):
        """Main execution flow."""
        try:
            # Generate dates
            start_date = "2026-02-02"
            end_date = "2026-04-30"
            date_range = pd.date_range(start=start_date, end=end_date)
            print(f"[#] Checking dates from {start_date} to {end_date}")

            self.login(email, password)
            self.navigate_to_internship()
            
            for date_val in date_range:
                self.process_entry(date_val)

            if self.missing_dates:
                print("\n" + "="*40)
                print("         NOT FILLED DATES         ")
                print("="*40)
                for md in self.missing_dates:
                    print(f"- {md}")
                print("="*40)
            else:
                print("\n[+] All checked dates are fully filled!")

            print("\n[***] Checking Task Completed! [***]")
        finally:
            input("\nPress Enter to close the browser...")
            self.driver.quit()

if __name__ == "__main__":
    
    print("=== VTU Internyet Diary Checker ===")
    
    # Get credentials from .env or prompt
    user_email = input("Enter VTU Email: ")
    user_pass = input("Enter VTU Password: ")
    
    checker = VTUDiaryChecker()
    checker.run(user_email, user_pass)
