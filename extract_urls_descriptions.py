import os
import signal
import sys
from dotenv import load_dotenv
import asyncio
import logging
import re
from datetime import datetime
import glob
from click_system import Macro
import time
import random
import win32clipboard
import win32con
import requests
import json 
import pyautogui
from PIL import Image
import os
# Moduli del progetto referenziati da main


# =============================================================================
# Configurazione base
# =============================================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)



# =============================================================================
# Helper indispensabili
# =============================================================================

def shutdown_handler(signal_received, frame):
    logger.warning("🛑 CTRL+C detected. Shutting down gracefully...")
    sys.exit(0)

def slugify(text: str) -> str:
    """Trasforma un titolo in uno slug sicuro per filename."""
    return re.sub(r'[^A-Za-z0-9]+', '_', text).strip('_')

def get_clipboard_content():
    """Legge testo dagli appunti di Windows (usato in più punti da main)."""
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
            data = win32clipboard.GetClipboardData(win32con.CF_TEXT).decode('utf-8')
        else:
            logger.error("❌ Clipboard non contiene testo in formato supportato.")
            data = None
    except Exception as e:
        logger.error(f"❌ Errore lettura clipboard: {e}")
        data = None
    finally:
        try:
            win32clipboard.CloseClipboard()
        except:
            pass
    return data or ""

def get_latest_download_name():
    """Ritorna il nome dell’ultimo file nella cartella Downloads (usato per rilevare nuovi file)."""
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    try:
        files = glob.glob(os.path.join(downloads_path, "*"))
        if files:
            latest = max(files, key=os.path.getmtime)
            return os.path.basename(latest)
    except Exception as e:
        logger.error(f"❌ Errore lettura Downloads: {e}")
    return None

def clean_and_review_html(content: str) -> str:
    """
    Pulizia finale HTML (usato in main post-SEO).
    Rimuove contenuti pre <h1>, residui di backtick, ecc.
    """
    logger.info("🧹 Starting enhanced HTML cleaning and review...")

    try:
        from bs4 import BeautifulSoup
        import re
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Rimuovi tutto prima del primo <h1>
        first_h1 = soup.find('h1')
        if first_h1:
            for element in list(first_h1.previous_siblings):
                element.decompose()
            parent = first_h1.parent
            while parent and parent.name not in ('body', '[document]'):
                for element in list(parent.previous_siblings):
                    element.decompose()
                parent = parent.parent
            logger.info("✂️ Removed content before first <h1> tag")
        
        content = str(soup)

        # Ripuliture varie
        content = re.sub(r"\b(?:html)?'''(?:html)?\b", '', content, flags=re.IGNORECASE)
        content = re.sub(r'(?i)(?:here\'s|here is)(?: the)? (?:html|code).*?\n', '', content)
        content = re.sub(r'(?i)the html code is.*?\n', '', content)
        content = re.sub(r'`+html', '', content, flags=re.IGNORECASE)
        content = re.sub(r'`+', '', content)
        
        return content.strip()
        
    except Exception as e:
        logger.error(f"❌ Error cleaning HTML: {str(e)}")
        return content

# =============================================================================
# MAIN
# =============================================================================

async def extract_url_description(number_to_download: str):
    pipeline_start = datetime.now()
    logger.info(f"Starting Urls extraction in Instagram content automation for: {number_to_download} Times")

    macro = Macro()
    extracted_urls = []


    instagram_saved_path = "https://www.instagram.com/la_veritas_news/saved/all-posts/"
    macro.replay_with_markers(
        marker_texts={
            "<f2>": (instagram_saved_path),
        },
        speed=1.0,
        actions_file="navigate_to_instagram.json"
    )
        # Loop for the number of times specified in number_to_download
    for _ in range(number_to_download):
        try:
            # --------- URL extraction via macro ----------
            max_attempts = 3
            attempt = 0
            initial_clipboard_content = get_clipboard_content()

            while attempt < max_attempts:
                attempt += 1
                logger.info("📝 Running URL extraction macro, attempt %d", attempt)

                macro.replay_with_markers(
                    marker_texts={
                        "<f2>": (instagram_saved_path)

                    },
                    speed=1.0,
                    actions_file="extract_urls.json"
                )

                time.sleep(3)
                url_extracted = get_clipboard_content()

                if not url_extracted.strip():
                    logger.warning("⚠️ url_extracted is empty. Retrying attempt %d...", attempt)
                    time.sleep(2)
                    continue

                if url_extracted.strip() == (initial_clipboard_content or "").strip():
                    logger.warning("⚠️ Clipboard content unchanged. Retrying attempt %d...", attempt)
                    time.sleep(2)
                    continue
                
                # If we got a valid URL, add it to our list
                if url_extracted.strip().startswith("https://www.instagram.com/"):
                    extracted_urls.append(url_extracted.strip())
                    logger.info(f"✅ Successfully extracted URL: {url_extracted.strip()}")
                    break

        except Exception as e:
            logger.error("❌ Error in url extraction: %s", e)

    # Update the JSON file with extracted URLs
    json_file_path = "instagram_urls.json"
    try:
        with open(json_file_path, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            data["content"][0]["title"] = extracted_urls
            data["content"][0]["urls"] = extracted_urls
            
            # Reset file pointer and write updated data
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
            logger.info(f"✅ Successfully saved {len(extracted_urls)} URLs to {json_file_path}")

    except Exception as e:
        logger.error(f"❌ Error updating JSON file: {e}")

    # Performance summary
    total_time = (datetime.now() - pipeline_start).total_seconds()
    logger.info("⏱️  PERFORMANCE SUMMARY:")
    logger.info("   • Total execution time: %.1fs (%.1f minutes)", total_time, total_time/60)
    logger.info("📊  CONTENT SUMMARY:")
    logger.info(f"   • URLs extracted: {len(extracted_urls)}")

    return extracted_urls





