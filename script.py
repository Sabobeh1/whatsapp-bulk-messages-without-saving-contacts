# Bulk WhatsApp sender using a CSV file with dynamic message templates
# Author @inforkgodara | Refactored by ChatGPT

import os
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from time import sleep, time
import pandas as pd

# ── 1. Load contacts and image ────────────────────────────────────────────────
# Required columns:
#   Number    – phone number with country code (no "+")
#   Name      – recipient's name
data = pd.read_csv("Marketing_expanded_full.csv")

# Path to the media file to be sent (image or video).
# Leave as "" or a non-existent path to send only text messages.
# IMPORTANT: Use the full path to the file if it's not in the same folder.
MEDIA_PATH = "test.mp4"  # e.g., "C:/Users/YourUser/Pictures/holiday_card.png"

# Check if the media file exists. The script will send the file only if the path is valid.
SEND_MEDIA = os.path.exists(MEDIA_PATH)
if MEDIA_PATH and not SEND_MEDIA:
    print(f"⚠️  Media file not found at '{MEDIA_PATH}'. The script will only send text messages.")
elif SEND_MEDIA:
    print(f"✅  Media file found at '{MEDIA_PATH}'. Script will send this file with captions.")

# ── 2. Launch WhatsApp Web ───────────────────────────────────────────────────
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)
driver.get("https://web.whatsapp.com")
input("Press ENTER after scanning the QR code and your chats are visible …")

# ── 3. Send personalised messages ───────────────────────────────────────────
failed_contacts = []
start_time = time()
total_messages = len(data)

for i, (_, row) in enumerate(data.iterrows()):
    # Clean phone number: remove spaces, hyphens, and ensure it starts with country code
    phone = str(row["رقم الجوال"]).replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone

    # Use a default template
    template ="""
مرحباً السادة {اسم المدير} المحترمين،
معكم سارة من شركة WM Marketing.

فيديوهات تحكي قصتك بأدق التفاصيل وباحترافية ما بتلاقيها إلا عندنا!
من التصوير الإبداعي، لمونتاج متقن، حتى الرسومات المتحركة والـ3D – كل شيء تحت سقف واحد.
نحول فكرتك لصورة حية تثير الإعجاب وتشد الانتباه.

✨ إذا بدكم فيديو يُظهر شغلكم بأفضل شكل، إحنا جاهزين نساعدكم.

ابعتوا "مهتم" وخلي فريقنا يتواصل معكم ليساعدكم.
"""

    # Replace {Name} placeholder
    try:
        personalised_text = template.format(**row.to_dict())
    except KeyError as err:
        print(f"⚠️  Missing column for placeholder {err} in row with phone {phone}")
        continue

    # The message is now sent by typing, so URL encoding is no longer needed.
    url = f"https://web.whatsapp.com/send?phone={phone}"
    print(f"Sending message {i+1}/{total_messages} to {phone}...")
    driver.get(url)

    try:
        # Wait for the main content area to load. This is a reliable way to know
        # the page has progressed. A 15-second timeout is a good balance.
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "main"))
        )

        # Check for the "Continue to Chat" button for numbers not saved in contacts.
        # This uses find_elements to avoid an exception if the button isn't found.
        continue_to_chat_buttons = driver.find_elements(By.XPATH, '//div[@role="button" and @title="Continue to Chat"]')
        if continue_to_chat_buttons:
            print(f"Clicking 'Continue to Chat' for {phone}...")
            continue_to_chat_buttons[0].click()

        # Wait for the chat input box to ensure the chat is ready for interaction.
        input_box_xpath = '//div[@contenteditable="true"][@data-tab="10"]'
        input_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, input_box_xpath))
        )

        if SEND_MEDIA:
            # Using abspath to ensure the file path is correct
            absolute_media_path = os.path.abspath(MEDIA_PATH)
            print(f"-> Attempting to send media from: {absolute_media_path}")

            # 1. Wait for and click the attach button using the new selector
            attach_button_xpath = '//button[@title="Attach"]'
            attach_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, attach_button_xpath))
            )
            attach_button.click()
            sleep(0.5) # Brief pause for the attach menu to open

            # 2. Find the hidden file input for "Photos & Videos" and send the media path
            media_input = driver.find_element(By.XPATH, '//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]')
            media_input.send_keys(absolute_media_path)
            
            # 3. Wait for the caption box using the more reliable aria-label
            caption_box_xpath = '//div[@aria-label="Add a caption"]'
            caption_box = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, caption_box_xpath))
            )
            
            # 4. Type the caption
            for line in personalised_text.split('\n'):
                caption_box.send_keys(line)
                caption_box.send_keys(Keys.SHIFT, Keys.ENTER)
            
            # Add a brief pause to ensure the send button is ready after typing
            sleep(1)

            # 5. Wait for and click the send button, using the more stable aria-label selector
            send_button_xpath = '//div[@aria-label="Send"]'
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, send_button_xpath))
            )
            send_button.click()

        else: # If not sending media, send a standard text message
            print("-> Sending text message...")
            # Type the message, splitting by newline characters
            for line in personalised_text.split('\n'):
                input_box.send_keys(line)
                input_box.send_keys(Keys.SHIFT, Keys.ENTER)
            input_box.send_keys(Keys.ENTER)

        # Increase sleep duration to allow media to upload and send completely.
        # This is crucial for larger files like videos.
        sleep(5)
        print(f"✅  Sent to {phone}: \"{personalised_text.replace('n', ' ')}\"")

    except Exception as e:
        # This will catch various errors, like invalid numbers or page load issues
        print(f"❌  Failed to send to {phone}. Please check the console for detailed errors.")
        print(f"   Error: {e}")
        failed_contacts.append(row)
        continue

end_time = time()
duration = end_time - start_time
messages_sent = total_messages - len(failed_contacts)

print(f"\n--- Sending Report ---")
print(f"Total time taken: {duration:.2f} seconds")
if messages_sent > 0:
    print(f"Average time per message: {duration / messages_sent:.2f} seconds")
print(f"Successfully sent: {messages_sent}/{total_messages}")
print(f"Failed to send: {len(failed_contacts)}/{total_messages}")
print("Browser will remain open. You can close it manually when done.")

# ── 4. Save failed contacts to a new CSV file ──────────────────────────────
if failed_contacts:
    print("\nSaving failed contacts to invalid_numbers.csv...")
    failed_df = pd.DataFrame(failed_contacts)
    # Reorder columns to match original if necessary, and drop pandas's name column
    failed_df = failed_df.rename_axis(None, axis=1)[data.columns]
    failed_df.to_csv("invalid_numbers.csv", index=False)
    print("✅  Saved invalid numbers to invalid_numbers.csv")

