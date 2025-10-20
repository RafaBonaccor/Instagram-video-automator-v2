"""
YouTube Video Downloader HD - Selezione automatica formato ottimale con CONTROLLI AUDIO

SOLUZIONI AL PROBLEMA DEI COOKIE:
1. CHIUDI CHROME prima di eseguire lo script (SOLUZIONE PIÙ SEMPLICE)
2. Oppure esporta i cookie manualmente (vedi istruzioni sotto)
3. Oppure usa Firefox invece di Chrome

SETUP:
pip install -U yt-dlp
"""

import yt_dlp
import os
import sys
import subprocess


def verifica_audio_video(filepath):
    """
    Verifica che il video abbia una traccia audio valida usando ffprobe
    Returns: (ha_audio, ha_video, durata_audio, durata_video)
    """
    try:
        # Usa ffprobe (incluso con ffmpeg) per controllare gli stream
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-show_format',
            filepath
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"⚠️  Impossibile verificare il file con ffprobe")
            return None, None, None, None
        
        import json
        data = json.loads(result.stdout)
        
        ha_video = False
        ha_audio = False
        durata_video = 0
        durata_audio = 0
        
        for stream in data.get('streams', []):
            codec_type = stream.get('codec_type', '')
            if codec_type == 'video':
                ha_video = True
                durata_video = float(stream.get('duration', 0))
            elif codec_type == 'audio':
                ha_audio = True
                durata_audio = float(stream.get('duration', 0))
        
        return ha_audio, ha_video, durata_audio, durata_video
        
    except Exception as e:
        print(f"⚠️  Errore nella verifica: {e}")
        return None, None, None, None


def scarica_video_hd(url, percorso_destinazione='./downloads', usa_cookies=True, file_cookies=None):
    """
    Scarica un video da YouTube in HD con selezione automatica del miglior formato
    e CONTROLLI AUDIO AVANZATI
    
    Args:
        url: URL del video YouTube
        percorso_destinazione: cartella dove salvare il video
        usa_cookies: se True, prova a usare i cookie (chiudi Chrome prima!)
        file_cookies: path al file cookies.txt (opzionale)
    """
    
    if not os.path.exists(percorso_destinazione):
        os.makedirs(percorso_destinazione)
    
    # Configurazione base con selezione automatica intelligente
    ydl_opts = {
        # FORMATO AUTOMATICO INTELLIGENTE CON PRIORITÀ ALL'AUDIO
        'format': (
            # Prova prima video+audio separati (migliore qualità)
            'bestvideo[ext=mp4][height>=1080]+bestaudio[ext=m4a]/bestvideo[ext=webm][height>=1080]+bestaudio/bestvideo[height>=1080]+bestaudio/'
            # Se non disponibili, prova 720p
            'bestvideo[ext=mp4][height>=720]+bestaudio[ext=m4a]/bestvideo[ext=webm][height>=720]+bestaudio/bestvideo[height>=720]+bestaudio/'
            # Se non disponibili, prova formati singoli HD
            'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/'
            # Fallback: prendi il migliore disponibile
            'best[ext=mp4]/best'
        ),
        
        'outtmpl': os.path.join(percorso_destinazione, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        
        # OPZIONI AUDIO CRITICHE
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        
        # Assicura che l'audio sia incluso
        'keepvideo': False,
        'prefer_ffmpeg': True,
        
        # IMPORTANTE: Permetti di scaricare qualsiasi formato disponibile
        'allow_unplayable_formats': False,
        'check_formats': True,
        
        # Anti-blocco
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'no_warnings': False,
        
        # User agent moderno
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        },
        
        'progress_hooks': [mostra_progresso],
        
        # Opzioni per gestire meglio gli errori
        'retries': 3,
        'fragment_retries': 3,
    }
    
    # Aggiungi cookie se richiesto
    if file_cookies and os.path.exists(file_cookies):
        ydl_opts['cookiefile'] = file_cookies
        print(f"🍪 Usando file cookie: {file_cookies}")
    elif usa_cookies:
        ydl_opts['cookiesfrombrowser'] = ('firefox',)
        print("🍪 Tentativo con cookie di Firefox...")
    
    try:
        print(f"\n🎬 Inizio download da: {url}")
        print(f"📁 Destinazione: {percorso_destinazione}\n")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("📡 Recupero informazioni video...")
            info = ydl.extract_info(url, download=False)
            
            print(f"\n📺 Titolo: {info['title']}")
            print(f"⏱️  Durata: {info.get('duration', 'N/A')} secondi")
            
            # CONTROLLO 1: Verifica che ci siano formati audio disponibili
            formati_con_audio = []
            if 'formats' in info:
                for f in info['formats']:
                    if f.get('acodec') and f.get('acodec') != 'none':
                        formati_con_audio.append(f)
            
            if not formati_con_audio:
                print("⚠️  ATTENZIONE: Nessun formato con audio trovato!")
                print("    Il video potrebbe essere senza audio o richiedere autenticazione.")
            else:
                print(f"✅ Trovati {len(formati_con_audio)} formati con audio disponibili")
            
            # Mostra informazioni sul formato selezionato
            if 'format' in info:
                print(f"🎥 Formato: {info.get('format', 'N/A')}")
            if 'height' in info:
                print(f"📐 Risoluzione: {info.get('height', 'N/A')}p")
            if 'ext' in info:
                print(f"📦 Estensione: {info.get('ext', 'N/A')}")
            
            # CONTROLLO 2: Verifica codec audio
            acodec = info.get('acodec', 'none')
            if acodec and acodec != 'none':
                print(f"🔊 Codec Audio: {acodec}")
            else:
                print("⚠️  ATTENZIONE: Formato selezionato senza audio!")
                
            filesize = info.get('filesize') or info.get('filesize_approx')
            if filesize and filesize > 0:
                size_mb = filesize / (1024*1024)
                print(f"💾 Dimensione: ~{size_mb:.1f} MB")
            
            print(f"\n⬇️  Inizio download...\n")
            ydl.download([url])
        
        # CONTROLLO 3: Verifica post-download con ffprobe
        print(f"\n🔍 Verifica integrità file...")
        
        # Trova il file scaricato
        expected_filename = ydl.prepare_filename(info)
        if os.path.exists(expected_filename):
            ha_audio, ha_video, dur_audio, dur_video = verifica_audio_video(expected_filename)
            
            if ha_audio is None:
                print("⚠️  Impossibile verificare l'audio (ffprobe non disponibile)")
                print("    Installa ffmpeg per abilitare i controlli: https://ffmpeg.org/download.html")
            elif not ha_audio:
                print("\n❌ PROBLEMA RILEVATO: Il video NON ha traccia audio!")
                print("\n🔧 SOLUZIONI:")
                print("1. Il video originale potrebbe essere senza audio")
                print("2. Prova a scaricare con i cookie (opzione 4 nel menu)")
                print("3. Prova con un formato specifico (opzione 3 nel menu)")
                print("\n💡 Vuoi riprovare con un formato diverso?")
            elif ha_video and abs(dur_audio - dur_video) > 1.0:
                print(f"\n⚠️  ATTENZIONE: Possibile disallineamento audio/video")
                print(f"    Durata video: {dur_video:.1f}s | Durata audio: {dur_audio:.1f}s")
            else:
                print("✅ Audio verificato correttamente!")
                print(f"   Durata audio: {dur_audio:.1f}s")
        
        print(f"\n✅ Download completato con successo!")
        print(f"📂 File salvato in: {os.path.abspath(percorso_destinazione)}")
        
    except yt_dlp.utils.DownloadError as e:
        errore = str(e)
        
        if "Requested format is not available" in errore:
            print(f"\n⚠️  Il formato richiesto non è disponibile!")
            print("🔍 Mostro i formati disponibili...\n")
            mostra_formati_disponibili(url)
            
        elif "Could not copy Chrome cookie" in errore or "cookie database" in errore.lower():
            print(f"\n❌ ERRORE: Chrome ha bloccato l'accesso ai cookie!")
            print("\n🔧 SOLUZIONI (scegli una):")
            print("\n   SOLUZIONE 1 (PIÙ SEMPLICE):")
            print("   1. CHIUDI completamente Chrome (verifica nel Task Manager)")
            print("   2. Riavvia questo script")
            print("\n   SOLUZIONE 2 (ALTERNATIVA):")
            print("   1. Usa Firefox invece di Chrome")
            print("   2. Apri YouTube in Firefox e fai login")
            print("   3. Riavvia lo script e scegli Firefox")
            print("\n   SOLUZIONE 3 (MANUALE):")
            print("   1. Installa l'estensione 'Get cookies.txt LOCALLY'")
            print("      https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc")
            print("   2. Vai su YouTube e clicca sull'estensione")
            print("   3. Salva il file cookies.txt nella cartella di questo script")
            print("   4. Riavvia lo script e scegli 'Usa file cookies.txt'\n")
            
        elif "403" in errore or "Forbidden" in errore:
            print(f"\n❌ ERRORE 403 FORBIDDEN!")
            print("\n🔧 PROVA QUESTI PASSAGGI:")
            print("1. Aggiorna yt-dlp: pip install -U yt-dlp")
            print("2. Pulisci la cache: yt-dlp --rm-cache-dir")
            print("3. Apri YouTube nel browser, fai login e riproduci un video")
            print("4. CHIUDI completamente il browser")
            print("5. Riprova il download")
            
        elif "nsig extraction failed" in errore:
            print(f"\n⚠️  Problema con l'estrazione della firma!")
            print("\n🔧 SOLUZIONI:")
            print("1. Aggiorna yt-dlp: pip install -U yt-dlp")
            print("2. Se il problema persiste, prova con i cookie")
            
        else:
            print(f"\n❌ Errore durante il download:")
            print(f"   {errore}")
            print("\n💡 Prova ad aggiornare yt-dlp: pip install -U yt-dlp")
            
    except Exception as e:
        print(f"\n❌ Errore generico: {str(e)}")


def mostra_formati_disponibili(url):
    """Mostra tutti i formati disponibili per il video CON INFORMAZIONI AUDIO"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'formats' in info:
                print("📋 FORMATI DISPONIBILI:\n")
                print(f"{'ID':<8} {'EXT':<6} {'RISOLUZIONE':<12} {'FPS':<5} {'AUDIO':<15} {'DIMENSIONE':<12} {'CODEC':<15}")
                print("-" * 85)
                
                for f in info['formats']:
                    format_id = f.get('format_id', 'N/A')
                    ext = f.get('ext', 'N/A')
                    resolution = f"{f.get('width', '?')}x{f.get('height', '?')}" if f.get('height') else 'audio only'
                    fps = str(f.get('fps', '-'))
                    
                    # INFORMAZIONI AUDIO
                    acodec = f.get('acodec', 'none')
                    if acodec and acodec != 'none':
                        abr = f.get('abr', 0)
                        audio_info = f"{acodec}@{int(abr)}k" if abr else acodec
                    else:
                        audio_info = "NO AUDIO"
                    
                    # Calcola dimensione
                    filesize = f.get('filesize') or f.get('filesize_approx', 0)
                    if filesize:
                        size_mb = filesize / (1024*1024)
                        size_str = f"{size_mb:.1f} MB"
                    else:
                        size_str = "N/A"
                    
                    vcodec = f.get('vcodec', 'none')[:14]
                    codec = vcodec if vcodec != 'none' else acodec
                    
                    print(f"{format_id:<8} {ext:<6} {resolution:<12} {fps:<5} {audio_info:<15} {size_str:<12} {codec:<15}")
                
                print("\n💡 SUGGERIMENTI:")
                print("   • Formati con 'NO AUDIO' devono essere combinati con un formato audio")
                print("   • Per scaricare: yt-dlp -f \"VIDEO_ID+AUDIO_ID\" URL")
                print("   • Esempio: yt-dlp -f \"270+234\" URL")
                print("   • Scegli formati con audio (es. m4a, opus) per combinare con video")
                
    except Exception as e:
        print(f"Impossibile recuperare i formati: {e}")


def mostra_progresso(d):
    """Mostra il progresso del download"""
    if d['status'] == 'downloading':
        percentuale = d.get('_percent_str', 'N/A').strip()
        velocita = d.get('_speed_str', 'N/A').strip()
        eta = d.get('_eta_str', 'N/A').strip()
        scaricato = d.get('_downloaded_bytes_str', 'N/A').strip()
        totale = d.get('_total_bytes_str', d.get('_total_bytes_estimate_str', 'N/A')).strip()
        
        print(f"\r⬇️  {percentuale} | {scaricato}/{totale} | 🚀 {velocita} | ⏱️  {eta}     ", end='', flush=True)
    elif d['status'] == 'finished':
        print(f"\n🔄 Download completato, unione audio/video in corso...")


def scarica_senza_cookies(url, percorso='./downloads'):
    """Scarica senza cookie (funziona per molti video pubblici)"""
    print("\n💡 Tentativo di download SENZA cookie...")
    print("   (Funziona per video pubblici senza restrizioni)\n")
    scarica_video_hd(url, percorso, usa_cookies=False)


def scarica_con_formato_specifico(url, formato_video, formato_audio, percorso='./downloads'):
    """Scarica con formato specifico (es. 270+234) CON VERIFICA AUDIO"""
    if not os.path.exists(percorso):
        os.makedirs(percorso)
    
    ydl_opts = {
        'format': f'{formato_video}+{formato_audio}',
        'outtmpl': os.path.join(percorso, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'progress_hooks': [mostra_progresso],
        'prefer_ffmpeg': True,
    }
    
    try:
        print(f"\n🎬 Download con formato: {formato_video}+{formato_audio}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"📺 Titolo: {info['title']}")
            
            ydl.download([url])
            
            # Verifica audio
            expected_filename = ydl.prepare_filename(info)
            if os.path.exists(expected_filename):
                print(f"\n🔍 Verifica audio...")
                ha_audio, ha_video, dur_audio, dur_video = verifica_audio_video(expected_filename)
                
                if ha_audio:
                    print("✅ Audio presente e funzionante!")
                elif ha_audio is False:
                    print("⚠️  ATTENZIONE: Nessuna traccia audio rilevata!")
        
        print("\n✅ Download completato!")
        
    except Exception as e:
        print(f"\n❌ Errore: {e}")


def menu_interattivo():
    """Menu interattivo migliorato"""
    print("=" * 70)
    print("🎥 YOUTUBE VIDEO DOWNLOADER HD - AUTO FORMAT CON CONTROLLI AUDIO")
    print("=" * 70)
    
    url = input("\n📎 Inserisci l'URL del video YouTube: ").strip()
    
    if not url:
        print("❌ URL non valido!")
        return
    
    print("\n🎯 Scegli modalità:")
    print("1. Download AUTOMATICO (consigliato - sceglie il miglior formato)")
    print("2. Vedi formati disponibili")
    print("3. Download con formato SPECIFICO (es. 270+234)")
    print("4. Download con cookie (per video privati/age-restricted)")
    
    scelta = input("\nScegli (1-4, default=1): ").strip() or "1"
    
    percorso = input("\n📂 Cartella di destinazione (default=./downloads): ").strip() or './downloads'
    
    if scelta == "1":
        scarica_senza_cookies(url, percorso)
    
    elif scelta == "2":
        print("\n🔍 Recupero formati disponibili...\n")
        mostra_formati_disponibili(url)
        
        ripeti = input("\n\nVuoi scaricare il video? (s/n): ").strip().lower()
        if ripeti == 's':
            scarica_senza_cookies(url, percorso)
    
    elif scelta == "3":
        print("\n📋 Prima vediamo i formati disponibili...")
        mostra_formati_disponibili(url)
        
        formato_video = input("\n🎥 ID formato VIDEO (es. 270): ").strip()
        formato_audio = input("🔊 ID formato AUDIO (es. 234): ").strip()
        
        if formato_video and formato_audio:
            scarica_con_formato_specifico(url, formato_video, formato_audio, percorso)
        else:
            print("❌ Formati non validi!")
    
    elif scelta == "4":
        print("\n🍪 Scegli browser per i cookie:")
        print("1. Firefox (consigliato)")
        print("2. Chrome (CHIUDI Chrome prima!)")
        print("3. File cookies.txt")
        
        cookie_choice = input("\nScegli (1-3): ").strip()
        
        if cookie_choice == "1":
            print("\n⚠️  Assicurati di essere loggato su YouTube in Firefox!")
            input("Premi INVIO per continuare...")
            ydl_opts_temp = {
                'format': (
                    'bestvideo[ext=mp4]+bestaudio[ext=m4a]/'
                    'bestvideo+bestaudio/'
                    'best'
                ),
                'outtmpl': os.path.join(percorso, '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'cookiesfrombrowser': ('firefox',),
                'progress_hooks': [mostra_progresso],
                'prefer_ffmpeg': True,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts_temp) as ydl:
                    ydl.download([url])
                print("\n✅ Download completato!")
            except Exception as e:
                print(f"\n❌ Errore: {e}")
        
        elif cookie_choice == "2":
            print("\n⚠️  IMPORTANTE:")
            print("   1. Assicurati di essere loggato su YouTube in Chrome")
            print("   2. CHIUDI completamente Chrome (controlla Task Manager)")
            input("\nPremi INVIO quando hai chiuso Chrome...")
            
            ydl_opts_temp = {
                'format': (
                    'bestvideo[ext=mp4]+bestaudio[ext=m4a]/'
                    'bestvideo+bestaudio/'
                    'best'
                ),
                'outtmpl': os.path.join(percorso, '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'cookiesfrombrowser': ('chrome',),
                'progress_hooks': [mostra_progresso],
                'prefer_ffmpeg': True,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts_temp) as ydl:
                    ydl.download([url])
                print("\n✅ Download completato!")
            except Exception as e:
                print(f"\n❌ Errore: {e}")
        
        elif cookie_choice == "3":
            file_cookies = input("\n📄 Percorso del file cookies.txt: ").strip()
            if os.path.exists(file_cookies):
                scarica_video_hd(url, percorso, usa_cookies=False, file_cookies=file_cookies)
            else:
                print(f"❌ File non trovato: {file_cookies}")


if __name__ == "__main__":
    # METODO 1: Menu interattivo (CONSIGLIATO)
    menu_interattivo()
    
    # METODO 2: Download automatico senza cookie
    # scarica_senza_cookies("https://www.youtube.com/watch?v=ESEMPIO")
    
    # METODO 3: Download con formato specifico
    # scarica_con_formato_specifico("URL", "270", "234")
    
    # METODO 4: Mostra solo i formati disponibili
    # mostra_formati_disponibili("URL")