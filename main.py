from instagram_download import InstagramDownloader  # Assicurati che il nome sia corretto
from extract_urls_descriptions import extract_url_description
import json
from download_insta_loop import start_instagram_editing
import asyncio
import sys
import time


if __name__ == "__main__":
    print("########################## Avvio del download dei video Instagram da main.py ##########################")
    file_path = "instagram_urls.json"  # Percorso al file JSON

    # 🔹 Numero di volte da eseguire il ciclo completo
    try:
        loop_count = int(input("Quante volte vuoi eseguire tutto il ciclo? (es. 3): "))
    except ValueError:
        loop_count = 1

    for i in range(loop_count):
        print(f"\n==================== 🔁 CICLO {i+1} di {loop_count} ====================")

        print("Avvio Estrazione degli URL da Instagram...")
        urls = asyncio.run(extract_url_description(1))  # ❗ NON TOCCATA

        try:
            print("Avvio del processo di editing")
            asyncio.run(start_instagram_editing(file_path))
        except KeyboardInterrupt:
            print("🛑 Execution interrupted manually")
            sys.exit(0)

        if not urls:
            print("✗ Nessun URL trovato nel file.")
        else:
            downloader = InstagramDownloader(output_folder="video_instagram")
            
            # Facoltativo: login
            # downloader.login("tuo_username", "tua_password")
            
            downloader.download_from_json()

        # 🔹 Pausa opzionale tra i cicli
        if i < loop_count - 1:
            print("\n⏳ Attendo 10 secondi prima del prossimo ciclo...\n")
            time.sleep(10)

    print("\n✅ Tutti i cicli completati con successo!")
