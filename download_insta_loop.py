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
from file_manager import FileManager
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
from instagram_download import InstagramDownloader
from event_emitter import emit_event, wait_for_discord_approval 
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

async def start_instagram_editing(number_to_download: str):
    pipeline_start = datetime.now()
    logger.info(f"Starting Instagram content automation")

    # First, download videos and descriptions from existing URLs

    downloader = InstagramDownloader(output_folder="video_instagram")
    
    # Download videos and get descriptions
    json_file_path = "instagram_urls.json"
    videos_desc_path = "videos_and_descriptions.json"
    
    try:
        # Read existing URLs
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not data.get("content", [{}])[0].get("urls"):
                logger.info("No existing URLs found to download. Proceeding with URL extraction...")
            else:
                logger.info(f"Found {len(data['content'][0]['urls'])} existing URLs to download")
                
                # Download videos with retry/skip logic
                download_successful = False
                while not download_successful:
                    # Attempt download
                    downloader.download_from_json(json_file_path)
                    
                    # Check if download was successful by reading results
                    try:
                        with open(videos_desc_path, 'r', encoding='utf-8') as f:
                            results = json.load(f)
                        
                        # Count failures
                        failed_count = sum(1 for r in results if r.get('filename') is None)
                        
                        if failed_count > 0:
                            logger.error(f"❌ {failed_count} video(s) failed to download")
                            
                            # Send Discord event with Retry/Skip buttons
                            event_id = f"DOWNLOAD_ERROR_{int(time.time())}"
                            webhook_url = "https://discordapp.com/api/webhooks/1428453862745968770/gk9gkmUPmtcNWx6F7hXtGC8ICu1PpodhvEP2REwm3LCw_yfQBNL3LnEB6J_QksOxd6cH"
                            
                            emit_event("DOWNLOAD_ERROR", {
                                "status": "error",
                                "event_id": event_id,
                                "failed_count": failed_count,
                                "total_count": len(results),
                                "message": f"Instagram download failed: {failed_count}/{len(results)} videos failed. Choose action:"
                            }, url=webhook_url)
                            
                            logger.info("⏸️ Waiting for user decision (Retry/Skip)...")
                            
                            # Wait for Discord approval
                            wait_for_discord_approval()
                            
                            # Check user decision
                            try:
                                with open("approved_description.txt", "r", encoding="utf-8") as f:
                                    decision = f.read().strip().lower()
                                
                                if decision == "skip":
                                    logger.info("⏭️ User chose to skip. Continuing with partial results...")
                                    download_successful = True  # Exit retry loop
                                elif decision == "retry":
                                    logger.info("🔄 User chose to retry. Attempting download again...")
                                    continue  # Retry the download
                                else:
                                    logger.warning(f"⚠️ Unknown decision '{decision}'. Retrying by default...")
                                    continue
                                    
                            except Exception as e:
                                logger.warning(f"⚠️ Could not read decision. Retrying by default: {e}")
                                continue
                        else:
                            # All downloads successful
                            download_successful = True
                            logger.info(f"✅ All {len(results)} videos downloaded successfully")
                            
                    except Exception as e:
                        logger.error(f"❌ Could not read results file: {e}")
                        download_successful = True  # Exit loop to avoid infinite retry
                    
                    # Create new JSON with videos and descriptions
                    with open(videos_desc_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    logger.info(f"✅ Saved videos and descriptions to {videos_desc_path}")
    
    except Exception as e:
        logger.error(f"❌ Error during video download: {e}")

    # Continue with the existing URL extraction process
    logger.info(f"Starting URLs extraction for {number_to_download} new items")
    macro = Macro()
    extracted_urls = []

    # Open Canva before editing
    logger.info("📂 Opening Canva...")
    macro.replay_with_markers(
        marker_texts={}, 
        speed=0.5,
        actions_file=FileManager.get_replay_path("canva_opener.json")
    )

    event_id = f"EDIT_CANVA_{int(time.time())}"
    url= "https://discordapp.com/api/webhooks/1428453862745968770/gk9gkmUPmtcNWx6F7hXtGC8ICu1PpodhvEP2REwm3LCw_yfQBNL3LnEB6J_QksOxd6cH"
    emit_event("EDIT_CANVA", {"status": "waiting", "event_id": event_id}, url=url)

    # 🔁 Fermati finché n8n non invia il “resume”

    wait_for_discord_approval()

    # ✅ Recupera la descrizione scritta dall’utente o fallback
    try:
        with open("approved_description.txt", "r", encoding="utf-8") as f:
            descrizione = f.read().strip()

        if not descrizione:
            descrizione = "Seguici per aiutarci nella nostra divulgazione della verità"
            logger.info("📄 Nessuna descrizione inserita su Discord. Usata descrizione di default.")
        else:
            logger.info(f"📄 Descrizione ricevuta da Discord: {descrizione}")

    except Exception as e:
        descrizione = "Seguici per aiutarci nella nostra divulgazione della verità"
        logger.warning(f"⚠️ Errore nel recupero descrizione. Usata default: {e}")



    macro.replay_with_markers(
        marker_texts={"<f2>": descrizione}, 
        speed=0.5,
        actions_file=FileManager.get_replay_path("download_from_canva.json")
    )
    time.sleep(100)

    logger.info("📝 Running Instagram upload")
    macro.replay_with_markers(
        marker_texts={"<f2>": descrizione}, 
        speed=0.5,
        actions_file=FileManager.get_replay_path("instagram_upload.json")
    )
    time.sleep(30)

    # Update the JSON file with extracted URLs

    # Performance summary
    total_time = (datetime.now() - pipeline_start).total_seconds()
    logger.info("⏱️  PERFORMANCE SUMMARY:")
    logger.info("   • Total execution time: %.1fs (%.1f minutes)", total_time, total_time/60)
    logger.info("📊  CONTENT SUMMARY:")
    logger.info(f"   • URLs extracted: {len(extracted_urls)}")

    return extracted_urls





