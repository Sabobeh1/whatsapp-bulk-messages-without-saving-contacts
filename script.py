# Bulk WhatsApp sender using a CSV file with dynamic message templates
# Author @inforkgodara | Refactored by ChatGPT

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote_plus
from time import sleep
import pandas as pd

# ── 1. Load contacts ─────────────────────────────────────────────────────────
# Required columns:
#   Number    – phone number with country code (no "+")
#   Name      – recipient's name
data = pd.read_csv("breakfast.csv")

# ── 2. Launch WhatsApp Web ───────────────────────────────────────────────────
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://web.whatsapp.com")
input("Press ENTER after scanning the QR code and your chats are visible …")

# ── 3. Send personalised messages ───────────────────────────────────────────
failed_contacts = []
for _, row in data.iterrows():
    # Clean phone number: remove spaces, hyphens, and ensure it starts with country code
    phone = str(row["Number"]).replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone

    # Use a default template
    template = "Hello {Name}, this is a test message from the WhatsApp bulk sender script!"

    # Replace {Name} placeholder
    try:
        personalised_text = template.format(**row.to_dict())
    except KeyError as err:
        print(f"⚠️  Missing column for placeholder {err} in row with phone {phone}")
        continue

    # URL-encode the final text (spaces → %20, line breaks → %0A, etc.)
    message = quote_plus(personalised_text)

    url = f"https://web.whatsapp.com/send?phone={phone}&text={message}"
    print(f"Attempting to send message to {phone}...")
    driver.get(url)

    try:
        # Wait for the main content area to load. This is a reliable way to know
        # the page has progressed. A 15-second timeout is a good balance for
        # speed and reliability.
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "main"))
        )
        
        # Use find_elements (plural) to check for the "Continue to Chat" button
        # without waiting. It returns an empty list if the element is not found.
        continue_to_chat_button = driver.find_elements(By.XPATH, '//div[@role="button"][@title="Continue to Chat"]')
        
        if continue_to_chat_button:
            # If the button exists, we are on the intermediate page.
            print(f"Clicking 'Continue to Chat' for {phone}...")
            continue_to_chat_button[0].click()
            # After clicking, we must explicitly wait for the input box to appear.
            input_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
            )
        else:
            # If the button doesn't exist, we should be on the chat page already.
            # We can find the input box directly. This will throw an error if not found,
            # which is caught by the 'except' block.
            input_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')

        # Now that we have the input_box, send the message.
        input_box.send_keys(Keys.ENTER)

        # A minimal sleep to ensure the message is sent before the browser navigates away.
        sleep(0.5)
        print(f"✅  Sent to {phone}: \"{personalised_text}\"")

    except Exception as e:
        # This will catch various errors, including:
        # - "main" container not loading (likely an invalid number pop-up)
        # - "Continue to Chat" was clicked but the input box never appeared
        # - Neither "Continue to Chat" nor the input box were found
        print(f"❌  Failed to send to {phone}. It might be an invalid number or a page load error.")
        failed_contacts.append(row)
        continue

print("\nAll messages have been sent. Browser will remain open. You can close it manually when done.")

# ── 4. Save failed contacts to a new CSV file ──────────────────────────────
if failed_contacts:
    print("\nSaving failed contacts to invalid_numbers.csv...")
    failed_df = pd.DataFrame(failed_contacts)
    # Reorder columns to match original if necessary, and drop pandas's name column
    failed_df = failed_df.rename_axis(None, axis=1)[data.columns]
    failed_df.to_csv("invalid_numbers.csv", index=False)
    print("✅  Saved invalid numbers to invalid_numbers.csv")
