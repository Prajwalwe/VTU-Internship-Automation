import os
from dotenv import load_dotenv
import time
import pandas as pd
from getpass import getpass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
    "fields": {
        "work_summary": "//label[contains(text(), 'Work Summary')]/..//textarea",
        "outcomes": "//label[contains(text(), 'Learnings')]/..//textarea",
        "blockers": "//label[contains(text(), 'Blockers')]/..//textarea",
        "skills": "//label[contains(text(), 'Skills Used')]/..//input",
        "hours": "//label[contains(text(), 'Hours worked')]/..//input",
        "links": "//label[contains(text(), 'Reference Links')]/..//textarea",
    },
    "save_button": "//button[normalize-space()='Save']",
}

class VTUDiaryAutomation:
    def __init__(self):
        self.setup_driver()
        self.wait = WebDriverWait(self.driver, 30)

    def setup_driver(self):
        """Initializes the Chrome WebDriver."""
        chrome_options = Options()
        # Uncomment the line below to run in headless mode (no browser window)
        # chrome_options.add_argument("--headless")
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

    def clear_and_fill(self, xpath, value):
        """Clears a field and fills it with a new value."""
        try:
            field = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            field.clear()
            # For some React fields, .clear() might not trigger an update event
            # So we select all and delete just in case
            from selenium.webdriver.common.keys import Keys
            field.send_keys(Keys.CONTROL + "a")
            field.send_keys(Keys.BACKSPACE)
            field.send_keys(str(value))
        except Exception as e:
            print(f"    [!] Warning: Could not fill field at {xpath}: {e}")

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
                    
                    old_header = current_header
                    self.driver.execute_script("arguments[0].click();", btn)
                    
                    # Wait for the calendar to update the header
                    try:
                        from selenium.webdriver.support.ui import WebDriverWait
                        WebDriverWait(self.driver, 3).until(
                            lambda d: d.find_element(By.XPATH, "//div[contains(@class, 'rdp-caption')] | //div[contains(@class, 'calendar-header')] | //h2 | //div[contains(@class, 'rdp-caption_label')]").text.lower() != old_header
                        )
                    except:
                        time.sleep(1) # Fallback wait
                        
                    time.sleep(2) # Additional small delay for calendar days to render

            # Click the day
            day_btn = None
            # 1. Try strict React Day Picker class matching
            try:
                strict_class_xpath = f"//button[contains(@class, 'rdp-day') and not(contains(@class, 'rdp-day_outside')) and text()='{target_day}']"
                day_btn = self.driver.find_element(By.XPATH, strict_class_xpath)
            except:
                # 2. Fallback Heuristic: Get all matching text buttons
                fallback_xpath = f"//button[normalize-space(text())='{target_day}' or normalize-space(.//text())='{target_day}']"
                btns = self.driver.find_elements(By.XPATH, fallback_xpath)
                
                if not btns:
                    raise NoSuchElementException(f"Could not find any button for day {target_day}")
                    
                # Filter out obviously disabled/outside ones if possible
                valid_btns = []
                for btn in btns:
                    html = btn.get_attribute('outerHTML').lower()
                    if 'outside' not in html and 'muted' not in html and 'disabled' not in html:
                        valid_btns.append(btn)
                        
                if len(valid_btns) == 1:
                    day_btn = valid_btns[0]
                else:
                    btns_to_use = valid_btns if len(valid_btns) > 1 else btns
                    # Heuristic: 
                    # If day > 15, previous month's day might be visible, current month's day is the LAST one.
                    # If day <= 15, next month's day might be visible, current month's day is the FIRST one.
                    if int(target_day) > 15:
                        day_btn = btns_to_use[-1]
                    else:
                        day_btn = btns_to_use[0]

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", day_btn)
            day_btn.click()
            time.sleep(1)
            print(f"    [+] Date {target_month} {target_day} selected.")
            
        except Exception as e:
            print(f"    [!] Error selecting date: {e}")
            self.driver.save_screenshot(f"date_error_{date_obj.strftime('%Y%m%d')}.png")
            raise e

    def process_entry(self, data_row):
        """Processes a single diary entry row."""
        date_val = pd.to_datetime(data_row['Date'])
        date_str = date_val.strftime("%Y-%m-%d")
        print(f"[>] Processing Date: {date_str}")

        # Skip Sundays
        if date_val.day_name() == 'Sunday':
            print(f"    [~] Skipping Sunday.")
            return

        # Skip empty rows
        if pd.isna(data_row['Work Summary']) or str(data_row['Work Summary']).strip() == "":
            print(f"    [~] Skipping empty row.")
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
            print("    [#] Clicked Continue. Waiting 5 seconds for form load...")
            time.sleep(5) # User requested 5s wait
            print("    [#] Navigation to form successful.")

            # 4. Fill the fields
            self.clear_and_fill(SELECTORS["fields"]["work_summary"], data_row['Work Summary'])
            self.clear_and_fill(SELECTORS["fields"]["outcomes"], data_row['Learning/Outcomes'])
            self.clear_and_fill(SELECTORS["fields"]["blockers"], data_row['Blockers/Risks'])
            self.clear_and_fill(SELECTORS["fields"]["hours"], data_row['Hours Worked'])
            self.clear_and_fill(SELECTORS["fields"]["links"], data_row['Links'])
            
            # Special handling for Skills (Multi-select)
            print("    [#] Clearing existing skills...")
            input_xpath = SELECTORS["fields"]["skills"]
            container_xpath = "//label[contains(text(), 'Skills Used')]/.."
            try:
                # 1. Try to click individual "remove" buttons for each chip
                remove_buttons = self.driver.find_elements(By.XPATH, f"{container_xpath}//*[contains(@class, 'remove')] | {container_xpath}//*[name()='svg' and contains(@class, 'cross')]")
                for btn in remove_buttons:
                    try:
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.2)
                    except:
                        pass
                
                # 2. Force-clear by sending BACKSPACE to the input field
                try:
                    input_field = self.driver.find_element(By.XPATH, input_xpath)
                    from selenium.webdriver.common.keys import Keys
                    from selenium.webdriver.common.action_chains import ActionChains
                    try:
                        parent_div = input_field.find_element(By.XPATH, "./ancestor::div[1]")
                        ActionChains(self.driver).move_to_element(parent_div).click().perform()
                    except:
                        self.driver.execute_script("arguments[0].click();", input_field)
                    
                    for _ in range(12): # Send backspace 12 times to delete any remaining chips
                        try:
                            input_field.send_keys(Keys.BACKSPACE)
                        except:
                            ActionChains(self.driver).send_keys(Keys.BACKSPACE).perform()
                        time.sleep(0.05)
                except:
                    pass
            except:
                pass

            raw_skills = str(data_row['Skills Used'])
            # Fix common spelling mistakes from Excel
            import re
            raw_skills = re.sub(r'(?i)andriod', 'Android', raw_skills)
            
            # Split by comma or newline
            skills_list = raw_skills.replace('\r', '').replace('\n', ',').split(',')
            
            # Ensure "Android Studio" is always added
            if not any(s.strip().lower() == "android studio" for s in skills_list):
                skills_list.append("Android Studio")

            for skill in skills_list:
                skill = skill.strip()
                if skill and skill.lower() != "nan":
                    try:
                        # Check if skill is already selected
                        existing_tags = self.driver.find_elements(By.XPATH, f"{container_xpath}//*[contains(@class, 'multiValue')] | {container_xpath}//div[contains(text(), '{skill}')]")
                        is_already_added = any(skill.lower() in tag.text.lower() for tag in existing_tags)
                        
                        if is_already_added:
                            print(f"    [~] Skill '{skill}' already added, skipping.")
                            continue

                        print(f"    [#] Adding skill: {skill}")
                        input_field = self.wait.until(EC.presence_of_element_located((By.XPATH, input_xpath)))
                        
                        # Scroll to input
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", input_field)
                        
                        # Focus the input using ActionChains on its parent div
                        from selenium.webdriver.common.action_chains import ActionChains
                        try:
                            parent_div = input_field.find_element(By.XPATH, "./ancestor::div[1]")
                            ActionChains(self.driver).move_to_element(parent_div).click().perform()
                        except:
                            self.driver.execute_script("arguments[0].click();", input_field)
                        
                        time.sleep(0.5) 
                        
                        # Send keys: try directly, if not interactable, send to active element
                        try:
                            input_field.send_keys(skill)
                        except:
                            ActionChains(self.driver).send_keys(skill).perform()
                        
                        # Wait dynamically for the dropdown options to load
                        print(f"    [#] Typed '{skill}'. Waiting for options to load...")
                        from selenium.webdriver.support.ui import WebDriverWait
                        lower_skill = skill.lower()
                        
                        def check_dropdown(d):
                            opts = d.find_elements(By.XPATH, "//div[@role='option']")
                            for opt in opts:
                                if opt.is_displayed() and lower_skill in opt.text.lower():
                                    return opt # Return the actual element if found!
                            msgs = d.find_elements(By.XPATH, "//*[contains(translate(text(), 'NOPRS', 'noprs'), 'no option') or contains(translate(text(), 'NORSULT', 'norsult'), 'no result')]")
                            for msg in msgs:
                                if msg.is_displayed():
                                    return "NO_OPTION"
                            return False
                            
                        try:
                            dropdown_result = WebDriverWait(self.driver, 10).until(check_dropdown)
                        except:
                            dropdown_result = "TIMEOUT"
                            
                        if dropdown_result == "NO_OPTION" or dropdown_result == "TIMEOUT":
                            print(f"    [!] '{skill}' was not found in dropdown.")
                            try:
                                # Re-find input field in case it went stale
                                input_field = self.driver.find_element(By.XPATH, input_xpath)
                                from selenium.webdriver.common.keys import Keys
                                input_field.send_keys(Keys.CONTROL + "a")
                                input_field.send_keys(Keys.BACKSPACE)
                            except:
                                pass
                            time.sleep(0.5)
                        else:
                            print("    [#] Option found! Clicking it...")
                            self.driver.execute_script("arguments[0].click();", dropdown_result)
                            print(f"    [+] '{skill}' was added")
                            time.sleep(1)
                            
                    except Exception as e:
                        print(f"    [!] Error while adding '{skill}': {e}")
                        pass

            # 5. Submit
            print("    [#] Scrolling to Save button...")
            try:
                save_btn = self.wait.until(EC.presence_of_element_located((By.XPATH, SELECTORS["save_button"])))
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", save_btn)
                print("    [#] Waiting 2 seconds before saving...")
                time.sleep(2)
                
                print(f"    [#] Clicking Save...")
                # Try multiple click methods
                try:
                    self.wait.until(EC.element_to_be_clickable((By.XPATH, SELECTORS["save_button"]))).click()
                except:
                    self.driver.execute_script("arguments[0].click();", save_btn)
                    
                print(f"{date_str} data has been saved")
            except Exception as e:
                print(f"    [!] Error clicking Save button: {e}")
                self.driver.save_screenshot(f"error_{date_str}.png")
                raise e
            
            # Navigate back to list for next entry without refreshing
            print(f"    [#] Waiting for automatic redirect to diary-entries...")
            self.wait.until(EC.url_contains("/diary-entries"))
            
            print(f"    [#] Navigating directly back to create form...")
            self.driver.get("https://vtu.internyet.in/dashboard/student/student-diary")
            # Wait for form/list to load
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Diary')] | //*[contains(text(), 'Android App Development')] | //button[@id='internship_id']")))
            print(f"    [+] Ready for next entry.")

        except Exception as e:
            print(f"    [!] Failed to process {date_str}: {e}")
            self.driver.get("https://vtu.internyet.in/dashboard/student/student-diary") # Reset

    def run(self, email, password, file_path):
        """Main execution flow."""
        try:
            # Read Data
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            print(f"[+] Loaded {len(df)} rows from {file_path}")

            # Filter to start from 2026-02-02
            start_date = pd.to_datetime("2026-05-01")
            df['Date'] = pd.to_datetime(df['Date'])
            df = df[df['Date'] >= start_date]
            print(f"[#] Filtered to start from {start_date.date()}. Remaining rows: {len(df)}")

            self.login(email, password)
            self.navigate_to_internship()
            
            for _, row in df.iterrows():
                self.process_entry(row)

            print("\n[***] Automation Task Completed! [***]")
        finally:
            input("\nPress Enter to close the browser...")
            self.driver.quit()

if __name__ == "__main__":
    load_dotenv() # Load variables from .env
    
    print("=== VTU Internyet Diary Automation ===")
    
    # Get credentials from .env or prompt
    user_email = os.getenv("VTU_EMAIL") or input("Enter VTU Email: ")
    user_pass = os.getenv("VTU_PASSWORD") or getpass("Enter VTU Password: ")
    
    # Get Excel path from .env or prompt
    excel_path = os.getenv("EXCEL_PATH")
    if not excel_path or excel_path == "":
        excel_path = input("Enter path to Excel/CSV file: ")
    
    # Cleanup path (remove quotes)
    excel_path = excel_path.strip('"').strip("'")

    automation = VTUDiaryAutomation()
    automation.run(user_email, user_pass, excel_path)
