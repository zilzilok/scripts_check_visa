import os
import re
import time
from io import BytesIO
from typing import Iterable, Tuple
from dotenv import load_dotenv

import requests
from pdfminer.high_level import extract_text
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()  # puts .env values into os.environ

TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

ID_NAME = {
    "587006": "Adel",
    "587884": "Amir",
}
PATTERN = re.compile(r'(?<!\d)(?:' + '|'.join(map(re.escape, ID_NAME.keys())) + r')(?!\d)')

URL = "https://belgrad.diplo.de/rs-de/service/05-visaeinreise/2631174-2631174"

def tg_send(text: str, parse_mode: str | None = None):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram not configured (missing TG_TOKEN or TG_CHAT_ID).")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print("Telegram send failed:", e)

def save_last_date(date: str, path="last_date.txt"):
    with open(path, "w", encoding="utf-8") as f:
        f.write(date)

def load_last_date(path="last_date.txt"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def fetch_pdf_text(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    }
    resp = requests.get(pdf_url, headers=headers, timeout=30)
    resp.raise_for_status()
    with BytesIO(resp.content) as bio:
        return extract_text(bio)

def find_ids(text: str) -> Tuple[list[str], list[str]]:
    found = sorted({m.group(0) for m in PATTERN.finditer(text)})
    missing = sorted(set(ID_NAME) - set(found))
    return found, missing


def build_message(
    date_text: str,
    found: Iterable[str],
    missing: Iterable[str]
) -> str:
    parts: list[str] = [f"✅ New date detected: {date_text}\n\n{URL}\n"]
    found = list(found)
    missing = list(missing)

    if found:
        parts.append("Found the following IDs:")
        parts += [f"• {iid} — {ID_NAME[iid]}" for iid in found]
    else:
        parts.append("No target IDs found.")

    if missing:
        parts.append("\nMissing IDs:")
        parts += [f"• {iid} — {ID_NAME[iid]}" for iid in missing]

    return "\n".join(parts)

# Selenium setup
def build_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")

    # point to Chromium binary
    opts.binary_location = "/usr/bin/chromium"  # or "/usr/bin/chromium-browser" if that exists

    # point to packaged chromedriver
    svc = Service("/usr/bin/chromedriver")

    return webdriver.Chrome(service=svc, options=opts)

driver = build_driver()
driver.get(URL)
wait = WebDriverWait(driver, 20)

last_date = load_last_date()
print("🔔 Bot started. Monitoring the page for date changes.")

try:
    while True:
        driver.refresh()

        try:
            # Wait for the list link to appear (more robust than immediate find)
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[title="Abholliste/Lista za preuzimanje - Kneza Milosa 75"]')))
            sub_span = element.find_element(By.CSS_SELECTOR, ".link-list__sub-content")

            # Extract date text (your original logic, kept)
            raw_text = sub_span.get_attribute("textContent")
            date_text = raw_text.split("/")[-1].strip() if raw_text else None

            print("Date:", date_text)

            # Notify only on change to avoid spam
            if date_text and date_text != last_date:
                pdf_url = element.get_attribute("href")
                if not pdf_url:
                    raise RuntimeError("Could not read the href attribute from the link element.")

                # Download the PDF bytes and fetch the text
                text = fetch_pdf_text(pdf_url)

                # Check IDs in the text
                found, missing = find_ids(text)

                # Build a human-readable response message
                message = build_message(date_text, found, missing)
                tg_send(message)
                last_date = date_text
                save_last_date(last_date)

        except Exception as e:
            print("⚠️ Something went wrong:", type(e).__name__, str(e))

        time.sleep(5)  # small pause before next refresh

except KeyboardInterrupt:
    print("🛑 Bot stopped by user.")
finally:
    driver.quit()
