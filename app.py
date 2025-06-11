import os
import uuid
import threading
import pandas as pd
from flask import Flask, request, render_template, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep, time

# ── 0. SETUP ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/qrcodes', exist_ok=True)

# In-memory dictionary to track the status of each bot session
SESSIONS = {}

# ── 1. BOT LOGIC (Adapted for Web UI) ────────────────────────────────────────
def run_whatsapp_bot(session_id: str, contacts_csv: str, number_column: str, image_path: str, message_template: str):
    """
    Manages a single WhatsApp bot instance, adapted for web interaction.
    """
    SESSIONS[session_id] = {'status': 'Starting', 'log': ['Bot session initialized...'], 'qr_path': None}

    def log(message):
        print(f"[{session_id}] {message}")
        SESSIONS[session_id]['log'].append(message)

    try:
        # ── Setup Chrome Profile ──────────────────────────────────────────────
        options = webdriver.ChromeOptions()
        profile_path = os.path.join(os.getcwd(), "chrome_profiles", session_id)
        os.makedirs(profile_path, exist_ok=True)
        options.add_argument(f"user-data-dir={profile_path}")
        options.add_argument("--headless=new") # Run headless for server environment
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,800")


        log("Loading contacts and setting up browser...")
        data = pd.read_csv(contacts_csv)
        if number_column not in data.columns:
            raise ValueError(f"Number column '{number_column}' not found in CSV.")
        
        SEND_IMAGE = os.path.exists(image_path)

        # ── Launch WhatsApp Web & Get QR Code ────────────────────────────────
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://web.whatsapp.com")

        log("Waiting for QR code...")
        sleep(5) # Give page time to load initial elements
        
        try:
            qr_canvas = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//canvas[@aria-label="Scan me!"]'))
            )
            qr_path = f"static/qrcodes/{session_id}.png"
            qr_canvas.screenshot(qr_path)
            SESSIONS[session_id]['qr_path'] = qr_path
            SESSIONS[session_id]['status'] = 'Scan QR Code'
            log(f"QR code saved to {qr_path}. Please scan it.")

            # Wait for user to scan QR code (i.e., wait for QR code to disappear)
            WebDriverWait(driver, 120).until_not(
                EC.presence_of_element_located((By.XPATH, '//canvas[@aria-label="Scan me!"]'))
            )
        except Exception as e:
             log(f"QR scan failed or timed out. Error: {e}")
             driver.quit()
             SESSIONS[session_id]['status'] = 'Error'
             return

        SESSIONS[session_id]['status'] = 'Sending Messages'
        log("Login successful! Starting to send messages...")
        
        # ── Send Personalised Messages ──────────────────────────────────────
        failed_contacts = []
        start_time = time()
        total_messages = len(data)

        for i, row in data.iterrows():
            phone = str(row[number_column]).replace(" ", "").replace("-", "")
            if not phone.startswith("+"):
                phone = "+" + phone
            
            try:
                personalised_text = message_template.format(**row.to_dict())
            except KeyError as err:
                log(f"⚠️ Missing column for placeholder {err}. Skipping {phone}")
                continue
            
            url = f"https://web.whatsapp.com/send?phone={phone}"
            log(f"({i+1}/{total_messages}) Opening chat with {phone}...")
            driver.get(url)

            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "main")))
                input_box_xpath = '//div[@contenteditable="true"][@data-tab="10"]'
                input_box = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, input_box_xpath))
                )

                if SEND_IMAGE:
                    attach_button_xpath = '//button[@title="Attach"]'
                    attach_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, attach_button_xpath)))
                    attach_button.click()
                    sleep(0.5)

                    image_input = driver.find_element(By.XPATH, '//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]')
                    image_input.send_keys(os.path.abspath(image_path))
                    
                    caption_box_xpath = '//div[@aria-label="Add a caption"]'
                    caption_box = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, caption_box_xpath)))
                    
                    for line in personalised_text.split('\\n'):
                        caption_box.send_keys(line)
                        caption_box.send_keys(Keys.SHIFT, Keys.ENTER)
                    
                    send_button_xpath = '//span[@data-icon="send"]'
                    send_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, send_button_xpath)))
                    send_button.click()
                else:
                    for line in personalised_text.split('\n'):
                        input_box.send_keys(line)
                        input_box.send_keys(Keys.SHIFT, Keys.ENTER)
                    input_box.send_keys(Keys.ENTER)

                sleep(1.5)
                log(f"✅ Sent to {phone}")

            except Exception as e:
                log(f"❌ Failed to send to {phone}. Error: {e}")
                failed_contacts.append(row)
                continue
        
        SESSIONS[session_id]['status'] = 'Completed'

    except Exception as e:
        log(f"An unexpected error occurred: {e}")
        SESSIONS[session_id]['status'] = 'Error'
    finally:
        if 'driver' in locals():
            driver.quit()
        log("Bot session finished.")


# ── 2. FLASK ROUTES ────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_columns', methods=['POST'])
def get_columns():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.csv'):
        try:
            df = pd.read_csv(file)
            return jsonify({'columns': list(df.columns)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/run_bot', methods=['POST'])
def start_bot():
    session_id = str(uuid.uuid4())
    
    contacts_file = request.files.get('contacts_file')
    image_file = request.files.get('image_file')
    number_column = request.form.get('number_column')
    message_template = request.form.get('message_template')

    if not all([contacts_file, number_column, message_template]):
        return jsonify({'error': 'Missing required form fields'}), 400

    contacts_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_contacts.csv")
    contacts_file.save(contacts_path)
    
    image_path = ""
    if image_file:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{image_file.filename}")
        image_file.save(image_path)

    thread = threading.Thread(
        target=run_whatsapp_bot,
        args=(session_id, contacts_path, number_column, image_path, message_template)
    )
    thread.start()

    return jsonify({'session_id': session_id})

@app.route('/api/status/<session_id>')
def get_status(session_id):
    session_info = SESSIONS.get(session_id)
    if not session_info:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(session_info)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 