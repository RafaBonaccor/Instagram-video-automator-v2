"""
Instagram Video Downloader - 2025 (Versione Automatizzata)
Scarica video Instagram con cookies automatici
"""

import yt_dlp
from pathlib import Path
import re
import json

class InstagramDownloader:
    def __init__(self, output_folder="instagram_downloads"):
        """Inizializza il downloader con cookies.txt automatico"""
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(exist_ok=True)
        
        # Configurazione yt-dlp con cookies.txt
        self.ydl_opts = {
            'outtmpl': str(self.output_folder / '%(title)s_%(id)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'format': 'best',
            'cookiefile': 'cookies.txt',  # Usa sempre cookies.txt
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            }
        }
        
        # Verifica che cookies.txt esista
        if not Path('cookies.txt').exists():
            print("⚠ ATTENZIONE: cookies.txt non trovato!")
            print("Crea il file cookies.txt con i cookies di Instagram")
            print("Alcuni download potrebbero fallire senza cookies\n")
        else:
            print("✓ Usando cookies.txt\n")
    
    def validate_url(self, url):
        """Verifica che l'URL sia valido"""
        patterns = [
            r'instagram\.com/p/[A-Za-z0-9_-]+',
            r'instagram\.com/reel/[A-Za-z0-9_-]+',
            r'instagram\.com/tv/[A-Za-z0-9_-]+',
        ]
        
        for pattern in patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def download_video(self, url):
        """Scarica un video da Instagram ed estrae la descrizione"""
        try:
            if not self.validate_url(url):
                print(f"✗ URL non valido: {url}")
                return False
            
            print(f"\n{'='*50}")
            print(f"Download: {url}")
            print('='*50)
            
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
            print(f"✓ Scaricato: {Path(filename).name}")
            
            # Estrai descrizione
            caption = info.get("description")
            if caption:
                print("\n📝 Descrizione del post:")
                print("-" * 40)
                print(caption)
                print("-" * 40)
                
                # (Opzionale) salva la descrizione in un file .txt
                desc_file = Path(filename).with_suffix(".txt")
                with open(desc_file, "w", encoding="utf-8") as f:
                    f.write(caption)
                print(f"✓ Descrizione salvata in: {desc_file.name}\n")
            else:
                print("⚠️ Nessuna descrizione trovata\n")

            return True
            
        except Exception as e:
            print(f"✗ Errore: {e}\n")
            return False

    
    def download_from_json(self, json_file="instagram_urls.json", output_json="videos_and_descriptions.json"):
        """Scarica video da file JSON e salva descrizioni collegate ai file"""
        try:
            if not Path(json_file).exists():
                print(f"✗ File non trovato: {json_file}")
                print(f"\nCrea un file '{json_file}' con questo formato:")
                print('{\n  "content": [\n    {"urls": ["https://www.instagram.com/reel/XXX/"]} \n  ]\n}')
                return
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            content = data.get('content', [{}])[0]
            urls = content.get('urls', [])

            if not urls:
                print("✗ Nessun URL trovato nel file JSON")
                return

            print(f"\n{'='*50}")
            print(f"Trovati {len(urls)} video da scaricare")
            print('='*50 + '\n')

            results = []
            successful = 0
            failed = 0

            for i, url in enumerate(urls, 1):
                print(f"[{i}/{len(urls)}] {url}")
                try:
                    with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        filename = ydl.prepare_filename(info)
                        description = info.get("description", "")

                        results.append({
                            "url": url,
                            "filename": Path(filename).name,
                            "description": description
                        })

                        successful += 1
                        print(f"✓ Scaricato: {Path(filename).name}")
                        print(f"✓ Descrizione estratta ({len(description)} caratteri)")
                except Exception as e:
                    print(f"✗ Errore per {url}: {e}")
                    results.append({
                        "url": url,
                        "filename": None,
                        "description": ""
                    })
                    failed += 1

            # Salva tutto nel file di output
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"\n✓ Dettagli salvati in {output_json}")

            print(f"\n{'='*50}")
            print("RIEPILOGO")
            print('='*50)
            print(f"✓ Scaricati: {successful}")
            print(f"✗ Falliti: {failed}")

        except json.JSONDecodeError:
            print(f"✗ Errore: {json_file} non è un JSON valido")
        except Exception as e:
            print(f"✗ Errore: {e}")



def main():
    """Funzione principale semplificata"""
    print("=" * 50)
    print("Instagram Video Downloader 2025")
    print("=" * 50)
    
    downloader = InstagramDownloader()
    
    print("Modalità:")
    print("1 - Scarica singolo video (inserisci URL)")
    print("2 - Scarica da file instagram_urls.json")
    
    choice = input("\nScegli modalità (1/2): ").strip()
    
    if choice == "1":
        url = input("\nInserisci URL del video Instagram: ").strip()
        if url:
            downloader.download_video(url)
        else:
            print("✗ URL vuoto")
    
    elif choice == "2":
        downloader.download_from_json()
    
    else:
        print("✗ Scelta non valida")


if __name__ == "__main__":
    main()