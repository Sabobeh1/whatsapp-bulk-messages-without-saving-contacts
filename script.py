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
        # Wait for either the message input box or the "Continue to Chat" button
        input_box = WebDriverWait(driver, 35).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
        )
        
        # Check if we need to click "Continue to Chat" button
        try:
            continue_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@role="button"][@title="Continue to Chat"]'))
            )
            print(f"Clicking 'Continue to Chat' for {phone}...")
            continue_button.click()
            sleep(2)  # Wait for chat to open
        except:
            # If no "Continue to Chat" button, we're already in the chat
            pass

        # Now try to send the message
        sleep(2)
        input_box.send_keys(Keys.ENTER)
        sleep(5)
        print(f"✅  Sent to {phone}: \"{personalised_text}\"")
    except Exception as e:
        print(f"❌  Could not open chat for {phone}")
        continue

print("\nAll messages have been sent. Browser will remain open. You can close it manually when done.")
