import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
import logging
from selenium.webdriver.common.by import By
import pyperclip
from pynput import keyboard, mouse
import datetime

try:
    from screeninfo import get_monitors
    SCREENINFO_AVAILABLE = True
except ImportError:
    SCREENINFO_AVAILABLE = False
    print("⚠️ screeninfo not available. Install with: pip install screeninfo")

ACTIONS_FILE = Path("actions.json")

def get_screen_resolution():
    """
    Get the primary screen resolution.
    Returns (width, height) tuple.
    Falls back to None if detection fails.
    """
    if not SCREENINFO_AVAILABLE:
        return None
    
    try:
        monitors = get_monitors()
        if monitors:
            # Use primary monitor (first one)
            primary = monitors[0]
            return (primary.width, primary.height)
    except Exception as e:
        print(f"⚠️ Could not detect screen resolution: {e}")
    
    return None
@dataclass
class RecordingMetadata:
    """Metadata about the recording session"""
    resolution: dict  # {"width": int, "height": int}
    version: str      # Format version for future compatibility


@dataclass
class Event:
    t: float          # tempo relativo (secondi dal via)
    type: str         # 'k_down','k_up','m_move','m_click','m_scroll','m_down','m_up'
    data: dict        # payload variabile

class Macro:
    def __init__(self, file_path=ACTIONS_FILE):
        self.file = Path(file_path)
        self.events: list[Event] = []
        self.paused = False
        self.should_stop = False
        self._keyboard_listener = None
        self.recording_metadata: RecordingMetadata = None
        self.resolution_transform = None  # (x_ratio, y_ratio) for.
        self.cached_resolution = None  # Cache screen resolution to avoid repeated queries


    def _setup_global_hotkeys(self):
        """Setup global hotkey listener"""
        def on_press(key):
            if key == keyboard.Key.f5:
                self.should_stop = True
                return False  # Stop listener
            elif key == keyboard.Key.f7:
                self.paused = not self.paused
                print("⏯️ Replay " + ("paused" if self.paused else "resumed"))
            
        self._keyboard_listener = keyboard.Listener(on_press=on_press)
        self._keyboard_listener.start()

        # ------------------------
    # RESOLUTION ADAPTATION
    # ------------------------
    def _calculate_transform_ratios(self, recorded_res, current_res):
        """
        Calculate coordinate transformation ratios.
        Returns (x_ratio, y_ratio) for scaling coordinates.
        """
        if not recorded_res or not current_res:
            return (1.0, 1.0)  # No transformation
        
        rec_width = recorded_res.get('width', 0)
        rec_height = recorded_res.get('height', 0)
        cur_width, cur_height = current_res
        
        # Prevent division by zero
        if rec_width == 0 or rec_height == 0:
            return (1.0, 1.0)
        
        x_ratio = cur_width / rec_width
        y_ratio = cur_height / rec_height
        
        return (x_ratio, y_ratio)
    
    def _transform_coordinates(self, x, y, x_ratio, y_ratio):
        """
        Apply coordinate transformation with bounds checking.
        Returns (x_new, y_new) as integers.
        """
        x_new = round(x * x_ratio)
        y_new = round(y * y_ratio)
        
        # Use cached screen bounds for clamping (avoid repeated queries)
        if self.cached_resolution:
            max_x, max_y = self.cached_resolution
            x_new = max(0, min(x_new, max_x - 1))
            y_new = max(0, min(y_new, max_y - 1))
        
        return (x_new, y_new)
    
    def get_resolution_info(self):
        """
        Get diagnostic information about resolution and transformation.
        Returns dict with current, recorded, and transformation info.
        """
        current_res = get_screen_resolution()
        info = {
            'current_resolution': current_res,
            'recorded_resolution': None,
            'transform_ratios': None,
            'transformation_active': False
        }
        
        if self.recording_metadata and self.recording_metadata.resolution:
            info['recorded_resolution'] = self.recording_metadata.resolution
            if current_res:
                ratios = self._calculate_transform_ratios(
                    self.recording_metadata.resolution,
                    current_res
                )
                info['transform_ratios'] = {'x_ratio': ratios[0], 'y_ratio': ratios[1]}
                info['transformation_active'] = (ratios != (1.0, 1.0))
        
        return info

    # ------------------------
    # REGISTRAZIONE
    # ------------------------
    def record(self):
        print("🔴 REGISTRAZIONE AVVIATA — premi ESC per fermare.")
        self.events.clear()
        start = time.perf_counter()
        stop_flag = {"stop": False}

        def now():
            return time.perf_counter() - start

        # --- Tastiera
        def on_press(key):
            if key == keyboard.Key.esc:
                stop_flag["stop"] = True
                return False  # stop listener
            self.events.append(Event(now(), "k_down", {"key": self._key_to_str(key)}))

        def on_release(key):
            # evita di registrare rilascio di ESC che ferma
            if key == keyboard.Key.esc:
                return
            self.events.append(Event(now(), "k_up", {"key": self._key_to_str(key)}))

        # --- Mouse
        def on_move(x, y):
            self.events.append(Event(now(), "m_move", {"x": x, "y": y}))

        def on_click(x, y, button, pressed):
            etype = "m_down" if pressed else "m_up"
            self.events.append(Event(now(), etype, {
                "x": x, "y": y, "button": str(button)  # es. 'Button.left'
            }))

        def on_scroll(x, y, dx, dy):
            self.events.append(Event(now(), "m_scroll", {"x": x, "y": y, "dx": dx, "dy": dy}))

        with keyboard.Listener(on_press=on_press, on_release=on_release) as k_listener, \
             mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll) as m_listener:
            while not stop_flag["stop"]:
                time.sleep(0.01)

        # Capture screen resolution
        screen_res = get_screen_resolution()
        if screen_res:
            print(f"📐 Screen resolution: {screen_res[0]}x{screen_res[1]}")
            self.recording_metadata = RecordingMetadata(
                resolution={'width': screen_res[0], 'height': screen_res[1]},
                version="2.0"
            )
        else:
            print("⚠️ Could not detect screen resolution - recording without metadata")
            self.recording_metadata = None
        # Save with metadata (new format) or fallback to old format
        try:
            if self.recording_metadata:
                # New format with metadata
                payload = {
                    'metadata': asdict(self.recording_metadata),
                    'events': [asdict(e) for e in self.events]
                }
            else:
                # Old format (backward compatibility)
                payload = [asdict(e) for e in self.events]
            
            self.file.write_text(json.dumps(payload, indent=2))
            print(f"✅ SALVATE {len(self.events)} azioni in {self.file.resolve()}")
        except Exception as e:
            print(f"❌ Errore salvataggio: {e}")
            # Fallback to old format
            payload = [asdict(e) for e in self.events]
            self.file.write_text(json.dumps(payload, indent=2))
            print(f"✅ SALVATE {len(self.events)} azioni (formato legacy)")

    # ------------------------
    # REPLAY
    # ------------------------
    def replay(self, speed=1.0):
        if not self.file.exists():
            print("❌ Nessuna registrazione trovata (actions.json mancante).")
            return

        # Carica eventi
        raw = json.loads(self.file.read_text())
        
        # Check if new format (with metadata) or old format (array)
        if isinstance(raw, dict) and 'metadata' in raw and 'events' in raw:
            # New format with metadata
            self.recording_metadata = RecordingMetadata(**raw['metadata'])
            self.events = [Event(e["t"], e["type"], e["data"]) for e in raw['events']]
            print(f"📐 Recorded at: {self.recording_metadata.resolution['width']}x{self.recording_metadata.resolution['height']}")
        else:
            # Old format (backward compatibility)
            self.events = [Event(e["t"], e["type"], e["data"]) for e in raw]
            self.recording_metadata = None
            print("⚠️ Old format detected (no resolution metadata)")
        
        # Calculate transformation ratios and cache current resolution
        current_res = get_screen_resolution()
        self.cached_resolution = current_res  # Cache to avoid repeated queries
        if current_res and self.recording_metadata:
            self.resolution_transform = self._calculate_transform_ratios(
                self.recording_metadata.resolution,
                current_res
            )
            if self.resolution_transform != (1.0, 1.0):
                print(f"📐 Current resolution: {current_res[0]}x{current_res[1]}")
                print(f"🔄 Applying coordinate transformation: x×{self.resolution_transform[0]:.3f}, y×{self.resolution_transform[1]:.3f}")
            else:
                print(f"✅ Resolution match - no transformation needed")
        else:
            self.resolution_transform = (1.0, 1.0)
        if not self.events:
            print("❌ File vuoto.")
            return

        print(f"▶️ REPLAY di {len(self.events)} eventi — premi ESC per interrompere.")
        kb = keyboard.Controller()
        ms = mouse.Controller()

        # Listener ESC per interrompere
        stop_flag = {"stop": False}
        def on_press(key):
            if key == keyboard.Key.esc:
                stop_flag["stop"] = True
                return False
        esc_listener = keyboard.Listener(on_press=on_press)
        esc_listener.start()

        t0 = time.perf_counter()
        last_t = 0.0

        try:
            for e in self.events:
                if stop_flag["stop"]:
                    print("⏹️ Replay interrotto.")
                    break
                # rispetta le tempistiche relative (con fattore speed)
                delay = max(0.0, (e.t - last_t) / max(1e-6, speed))
                if delay > 0:
                    time.sleep(delay)
                last_t = e.t

                # esegui evento
                if e.type == "k_down":
                    self._key_action(kb, e.data["key"], down=True)
                elif e.type == "k_up":
                    self._key_action(kb, e.data["key"], down=False)
                elif e.type == "m_move":
                    x, y = self._transform_coordinates(e.data["x"], e.data["y"], *self.resolution_transform)
                    ms.position = (x, y)
                elif e.type == "m_down":
                    x, y = self._transform_coordinates(e.data["x"], e.data["y"], *self.resolution_transform)
                    ms.position = (x, y)
                    ms.press(self._mouse_button(e.data["button"]))
                elif e.type == "m_up":
                    x, y = self._transform_coordinates(e.data["x"], e.data["y"], *self.resolution_transform)
                    ms.position = (x, y)
                    ms.release(self._mouse_button(e.data["button"]))
                elif e.type == "m_scroll":
                    x, y = self._transform_coordinates(e.data["x"], e.data["y"], *self.resolution_transform)
                    ms.position = (x, y)
                    ms.scroll(e.data["dx"], e.data["dy"])
        finally:
            esc_listener.stop()
            elapsed = time.perf_counter() - t0
            print(f"✅ REPLAY COMPLETATO in {elapsed:.2f}s")


    def replay_with_markers(self, marker_texts=None, speed=1.0, per_char_delay=0.02,
                    clear_before=True, swallow_window=8.0, actions_file=None):
        """
        Replay con marcatori dinamici - ora supporta auto-conversione formato verbose
        """
        if marker_texts is None:
            marker_texts = {}

        # Use provided actions file or default
        json_file = Path(actions_file) if actions_file else self.file
        
        if not json_file.exists():
            print(f"❌ File azioni non trovato: {json_file}")
            return

        # Reset control flags
        self.paused = False
        self.should_stop = False
        
        # Setup global hotkey listener
        self._setup_global_hotkeys()
        
        try:
            raw_data = json.loads(json_file.read_text())
            
            # Check if new format (with metadata) or old format (array)
            if isinstance(raw_data, dict) and 'metadata' in raw_data and 'events' in raw_data:
                # New format with metadata
                self.recording_metadata = RecordingMetadata(**raw_data['metadata'])
                print(f"📐 Recorded at: {self.recording_metadata.resolution['width']}x{self.recording_metadata.resolution['height']}")
                # Use events from metadata format
                events_data = raw_data['events']
            else:
                # Old format (backward compatibility) or verbose format
                self.recording_metadata = None
                events_data = raw_data
            
            # Calculate transformation ratios and cache current resolution
            current_res = get_screen_resolution()
            self.cached_resolution = current_res  # Cache to avoid repeated queries
            if current_res and self.recording_metadata:
                self.resolution_transform = self._calculate_transform_ratios(
                    self.recording_metadata.resolution,
                    current_res
                )
                if self.resolution_transform != (1.0, 1.0):
                    print(f"📐 Current resolution: {current_res[0]}x{current_res[1]}")
                    print(f"🔄 Applying coordinate transformation: x×{self.resolution_transform[0]:.3f}, y×{self.resolution_transform[1]:.3f}")
                else:
                    print(f"✅ Resolution match - no transformation needed")
            else:
                self.resolution_transform = (1.0, 1.0)
                if not self.recording_metadata:
                    print("⚠️ Old format detected (no resolution metadata)")
            
            # AUTO-CONVERSIONE: rileva e converte formato verbose
            if self._is_verbose_format(events_data):
                print(f"🔄 Rilevato formato verbose, comprimendo {len(events_data)} eventi...")
                compressed_data = self._auto_compress_verbose(events_data)
                print(f"✅ Compressi in {len(compressed_data)} azioni")
                
                # Converti in Event objects
                self.events = []
                for item in compressed_data:
                    if item['type'] == 'type_text':
                        # Simula digitazione carattere per carattere
                        text = item['data']['text']
                        for i, char in enumerate(text):
                            char_time = item['t'] + (i * per_char_delay)
                            self.events.append(Event(char_time, "k_down", {"key": char}))
                            self.events.append(Event(char_time + 0.01, "k_up", {"key": char}))
                    elif item['type'] == 'drag':
                        # Converte drag in sequenza m_down + m_move + m_up
                        self.events.append(Event(item['t'], "m_down", {
                            'x': item['data']['start']['x'], 
                            'y': item['data']['start']['y'], 
                            'button': item['data']['button']
                        }))
                        # Path intermedio
                        path = item['data'].get('path', [])
                        for j, pt in enumerate(path[1:-1], 1):  # Salta primo e ultimo
                            move_time = item['t'] + (j * 0.02)
                            self.events.append(Event(move_time, "m_move", {'x': pt['x'], 'y': pt['y']}))
                        # Release finale  
                        end_time = item['t'] + len(path) * 0.02
                        self.events.append(Event(end_time, "m_up", {
                            'x': item['data']['end']['x'],
                            'y': item['data']['end']['y'], 
                            'button': item['data']['button']
                        }))
                    else:
                        # Evento normale
                        self.events.append(Event(item['t'], item['type'], item['data']))
            else:
                # Formato normale
                self.events = [Event(e["t"], e["type"], e["data"]) for e in events_data]
                
        except Exception as e:
            print(f"❌ Errore caricamento file {json_file}: {e}")
            return

        # Il resto del metodo rimane identico...
        if not self.events:
            print("❌ File vuoto.")
            return

        print(f"▶️ REPLAY (con marker) di {len(self.events)} eventi da {json_file}")
        kb = keyboard.Controller()
        ms = mouse.Controller()

        stop_flag = {"stop": False}
        def _on_press(key):
            if key == keyboard.Key.esc:
                stop_flag["stop"] = True
                return False
        esc_listener = keyboard.Listener(on_press=_on_press)
        esc_listener.start()

        def is_printable(k: str) -> bool:
            # tasto 'a','b','1',',', ecc. (non <enter>, <ctrl>...)
            return isinstance(k, str) and len(k) == 1

        # stato swallow per ignorare le battute registrate dopo un marker
        swallowing = False
        swallow_until_t = 0.0
        skip_keyup = set()
        last_t = 0.0

        try:
            for e in self.events:
                # Check for stop signal
                if self.should_stop:
                    print("⏹️ Replay stopped with F5")
                    break
                
                # Check and handle pause
                while self.paused:
                    time.sleep(0.1)
                    if self.should_stop:
                        break
                
                if stop_flag["stop"]:
                    print("⏹️ Replay interrotto.")
                    break

                # tempi relativi
                delay = max(0.0, (e.t - last_t) / max(1e-6, speed))
                if delay > 0:
                    time.sleep(delay)
                last_t = e.t

                # confini che disattivano lo swallow
                def boundary_event(ev) -> bool:
                    if ev.type.startswith("m_"):  # qualsiasi click/scroll/move
                        return True
                    if ev.type == "k_down" and ev.data.get("key") in ("<enter>", "<tab>", "<esc>"):
                        return True
                    if ev.type == "k_down" and ev.data.get("key") in marker_texts:
                        return True
                    return False

                # se stiamo inghiottendo e passiamo il tempo max, termina swallow
                if swallowing and (e.t > swallow_until_t):
                    swallowing = False

                # se evento di confine, termina swallow ma NON saltare l’evento
                if swallowing and boundary_event(e):
                    swallowing = False  # poi l'evento viene eseguito normalmente

                # ---- MARKER ----
                if e.type == "k_down" and e.data.get("key") in marker_texts:
                    val = marker_texts[e.data["key"]]

                    # 0) opzionale: pulisci campo (Ctrl+A, Backspace)

                    kb.press(keyboard.Key.ctrl); kb.press('a')
                    kb.release('a'); kb.release(keyboard.Key.ctrl)
                    time.sleep(0.05)
                    kb.press(keyboard.Key.backspace); kb.release(keyboard.Key.backspace)
                    time.sleep(0.05)


                    # 1) handler file: {"file": "...", "enter": True, "sleep": 1.0}
                    if isinstance(val, dict) and "file" in val:
                        path = val["file"]
                        text = val if isinstance(val, str) else val.get("text", "")
                        pyperclip.copy(text)
                        time.sleep(0.05)

                        # Incolla con Ctrl+V
                        kb.press(keyboard.Key.ctrl)
                        kb.press('v')
                        kb.release('v')
                        kb.release(keyboard.Key.ctrl)

                        time.sleep(0.05)  # piccola pausa dopo incolla
                        if val.get("enter", True):
                            kb.press(keyboard.Key.enter); kb.release(keyboard.Key.enter)
                        if val.get("sleep"):
                            try:
                                time.sleep(float(val["sleep"]))
                            except Exception:
                                pass
                    else:
                        # 2) handler testo: stringa o {"text": "..."}
                        text = val if isinstance(val, str) else val.get("text", "")
                        pyperclip.copy(text)
                        time.sleep(0.05)

                        # Incolla con Ctrl+V
                        kb.press(keyboard.Key.ctrl)
                        kb.press('v')
                        kb.release('v')
                        kb.release(keyboard.Key.ctrl)

                        time.sleep(0.05)  # piccola pausa dopo incolla

                    # dopo il marker, inghiotti i caratteri registrati per un po'
                    swallowing = True
                    swallow_until_t = e.t + float(swallow_window)
                    skip_keyup.add(e.data["key"])
                    continue  # non eseguire il keydown del marker

                if e.type == "k_up" and e.data.get("key") in skip_keyup:
                    skip_keyup.discard(e.data["key"])
                    continue  # non eseguire il keyup del marker

                # durante swallow, salta i caratteri “stampabili” (evita doppie battute)
                if swallowing and e.type in ("k_down", "k_up"):
                    k = e.data.get("key")
                    if is_printable(k):
                        continue  # ignora le lettere registrate

                # ---- ESECUZIONE STANDARD ----
                if e.type == "k_down":
                    self._key_action(kb, e.data["key"], down=True)
                elif e.type == "k_up":
                    self._key_action(kb, e.data["key"], down=False)
                elif e.type == "m_move":
                    x, y = self._transform_coordinates(e.data["x"], e.data["y"], *self.resolution_transform)
                    ms.position = (x, y)
                elif e.type == "m_down":
                    x, y = self._transform_coordinates(e.data["x"], e.data["y"], *self.resolution_transform)
                    ms.position = (x, y)
                    ms.press(self._mouse_button(e.data["button"]))
                elif e.type == "m_up":
                    x, y = self._transform_coordinates(e.data["x"], e.data["y"], *self.resolution_transform)
                    ms.position = (x, y)
                    ms.release(self._mouse_button(e.data["button"]))
                elif e.type == "m_scroll":
                    x, y = self._transform_coordinates(e.data["x"], e.data["y"], *self.resolution_transform)
                    ms.position = (x, y)
                    ms.scroll(e.data["dx"], e.data["dy"])

                # Add pause check after each action
                if self.paused:
                    continue

        finally:
            if self._keyboard_listener:
                self._keyboard_listener.stop()
                self._keyboard_listener = None
            esc_listener.stop()
            print("✅ REPLAY COMPLETATO")



    # ------------------------
    # Utility key/mouse
    # ------------------------
    @staticmethod
    def _key_to_str(key):
        # Converti Key/char in stringa serializzabile
        try:
            return key.char  # normali caratteri
        except AttributeError:
            return f"<{key.name}>"  # tasti speciali, es. <ctrl>, <shift>, <enter>

    @staticmethod
    def _parse_key(s):
        if s.startswith("<") and s.endswith(">"):
            name = s[1:-1]
            # mappa ai Key speciali
            return getattr(keyboard.Key, name)
        else:
            return s  # singolo carattere

    @staticmethod
    def _mouse_button(name):
        # name es. 'Button.left', 'Button.right', 'Button.middle'
        if name.endswith("left"):
            return mouse.Button.left
        if name.endswith("right"):
            return mouse.Button.right
        if name.endswith("middle"):
            return mouse.Button.middle
        # fallback
        return mouse.Button.left

    @staticmethod
    def _key_action(kb: keyboard.Controller, s: str, down: bool):
        k = Macro._parse_key(s)
        try:
            if isinstance(k, keyboard.Key):
                if down: kb.press(k)
                else:    kb.release(k)
            else:
                # carattere singolo
                if down: kb.press(k)
                else:    kb.release(k)
        except Exception:
            pass

    def _is_verbose_format(self, events_data):
        """Rileva se il formato è verbose, anche con t_start invece di t"""
        if not events_data or len(events_data) < 5:
            return False
        
        # Check for 't_start' and known verbose keys like 'params'
        sample = events_data[0]
        return 'params' in sample and ('t_start' in sample or 't_end' in sample)


    def _auto_compress_verbose(self, events_data):
        """Comprime formato verbose (con t_start) in comandi essenziali"""
        compressed = []
        i = 0
        
        def get_time(e):
            return e.get('t_start', e.get('t', 0.0))  # fallback per compatibilità
        
        while i < len(events_data):
            e = events_data[i]
            event_type = e['type']
            t = get_time(e)

            if event_type == 'click':
                compressed.append({
                    't': t,
                    'type': 'm_down',
                    'data': {'x': e['params']['x'], 'y': e['params']['y'], 'button': e['params']['button']}
                })
                compressed.append({
                    't': e.get('t_end', t + 0.05),
                    'type': 'm_up',
                    'data': {'x': e['params']['x'], 'y': e['params']['y'], 'button': e['params']['button']}
                })

            elif event_type == 'key_press':
                key = e['params']['key']
                compressed.append({'t': t, 'type': 'k_down', 'data': {'key': key}})
                compressed.append({'t': e.get('t_end', t + 0.01), 'type': 'k_up', 'data': {'key': key}})

            elif event_type == 'drag':
                drag_data = e['params']
                start = drag_data['start']
                end = drag_data['end']
                path = drag_data.get('path', [])
                compressed.append({
                    't': t,
                    'type': 'drag',
                    'data': {
                        'button': drag_data['button'],
                        'start': start,
                        'end': end,
                        'path': path
                    }
                })
            
            i += 1
        
        return compressed

    
    def _is_printable_key(self, key_str):
        """Controlla se è carattere stampabile"""
        return isinstance(key_str, str) and len(key_str) == 1 and key_str.isprintable()

class ClickSaveSystem:
    def __init__(self, driver):
        self.driver = driver
        self.logger = logging.getLogger("ClickSave")
        self.config_file = "textarea_config.json"
        self.saved_selector = None
        self.load_config()
    
    def load_config(self):
        """Carica configurazione salvata"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.saved_selector = config.get('selector')
                if self.saved_selector:
                    self.logger.info(f"✅ Configurazione caricata: {self.saved_selector}")
                    return True
        except FileNotFoundError:
            self.logger.info("📝 Nessuna configurazione trovata")
        except Exception as e:
            self.logger.warning(f"⚠️ Errore caricamento config: {e}")
        return False
    
    def save_config(self, selector):
        """Salva configurazione"""
        try:
            config = {
                'selector': selector,
                'timestamp': time.time(),
                'url': self.driver.current_url
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            self.saved_selector = selector
            self.logger.info(f"💾 Configurazione salvata: {selector}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Errore salvataggio: {e}")
            return False
    
    def setup_click_capture(self):
        """Setup per catturare click del mouse"""
        print("\n🎯 SETUP CLICK & SAVE")
        print("=" * 50)
        print("📋 Istruzioni:")
        print("1. Tra 3 secondi, clicca SUL CAMPO TEXTAREA")
        print("2. Il sistema identificherà automaticamente l'elemento")
        print("3. Lo salverà per usi futuri")
        print("=" * 50)
        
        # Countdown
        for i in range(3, 0, -1):
            print(f"🕐 {i}...")
            time.sleep(1)
        
        print("👆 CLICCA SUL CAMPO TEXTAREA ORA!")
        
        # JavaScript per catturare il prossimo click
        capture_script = """
        window.clickedElement = null;
        window.clickHandler = function(event) {
            window.clickedElement = event.target;
            document.removeEventListener('click', window.clickHandler);
            
            // Highlight element
            event.target.style.outline = '3px solid red';
            event.target.style.outlineOffset = '2px';
            
            console.log('Element captured:', event.target);
        };
        document.addEventListener('click', window.clickHandler);
        return true;
        """
        
        self.driver.execute_script(capture_script)
        
        # Aspetta il click (max 30 secondi)
        for i in range(30):
            try:
                element_info = self.driver.execute_script("""
                if (window.clickedElement) {
                    let el = window.clickedElement;
                    return {
                        tagName: el.tagName,
                        id: el.id,
                        className: el.className,
                        placeholder: el.placeholder || '',
                        xpath: getXPath(el),
                        attributes: Array.from(el.attributes).map(attr => ({
                            name: attr.name,
                            value: attr.value
                        }))
                    };
                }
                return null;
                
                function getXPath(element) {
                    if (element.id !== '') {
                        return 'id("' + element.id + '")';
                    }
                    if (element === document.body) {
                        return element.tagName;
                    }
                    
                    var ix = 0;
                    var siblings = element.parentNode.childNodes;
                    for (var i = 0; i < siblings.length; i++) {
                        var sibling = siblings[i];
                        if (sibling === element) {
                            return getXPath(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
                        }
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                            ix++;
                        }
                    }
                }
                """)
                
                if element_info:
                    print(f"\n✅ ELEMENTO CATTURATO!")
                    print(f"📝 Tag: {element_info['tagName']}")
                    print(f"🆔 ID: {element_info['id']}")
                    print(f"📋 Placeholder: {element_info['placeholder']}")
                    print(f"🎯 XPath: {element_info['xpath']}")
                    
                    # Genera selettore ottimale
                    selector = self.generate_optimal_selector(element_info)
                    print(f"🔧 Selettore generato: {selector}")
                    
                    # Testa il selettore
                    if self.test_selector(selector):
                        print("✅ Selettore testato e funzionante!")
                        self.save_config(selector)
                        return selector
                    else:
                        print("❌ Selettore non funziona, riprovare...")
                        return None
                        
            except Exception as e:
                pass
                
            time.sleep(1)
            print(".", end="", flush=True)
        
        print("\n❌ Timeout - nessun click rilevato")
        return None
    
    def generate_optimal_selector(self, element_info):
        """Genera il selettore CSS ottimale"""
        # Strategia: prova in ordine di specificità
        
        # 1. ID (più specifico)
        if element_info['id']:
            return f"#{element_info['id']}"
        
        # 2. Placeholder (molto specifico per textarea)
        if element_info['placeholder']:
            return f'{element_info["tagName"].lower()}[placeholder="{element_info["placeholder"]}"]'
        
        # 3. Combinazione tag + classi importanti
        if element_info['className']:
            # Estrai classi chiave
            classes = element_info['className'].split()
            key_classes = [c for c in classes if any(keyword in c.lower() 
                          for keyword in ['textarea', 'input', 'field', 'composer'])]
            
            if key_classes:
                class_selector = '.' + '.'.join(key_classes[:3])  # Max 3 classi
                return f'{element_info["tagName"].lower()}{class_selector}'
        
        # 4. Attributi specifici
        for attr in element_info['attributes']:
            if attr['name'] in ['rows', 'data-testid', 'aria-label']:
                return f'{element_info["tagName"].lower()}[{attr["name"]}="{attr["value"]}"]'
        
        # 5. Fallback: tag + classi principali
        if element_info['className']:
            main_classes = element_info['className'].split()[:2]  # Prime 2 classi
            if main_classes:
                return f'{element_info["tagName"].lower()}.{".".join(main_classes)}'
        
        # 6. Ultimate fallback: solo tag
        return element_info["tagName"].lower()
    
    def test_selector(self, selector):
        """Testa se il selettore funziona"""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if elements and len(elements) > 0:
                element = elements[0]
                if element.is_displayed() and element.is_enabled():
                    # Test di interazione
                    element.click()
                    time.sleep(0.2)
                    return True
            return False
        except Exception as e:
            self.logger.warning(f"⚠️ Test selettore fallito: {e}")
            return False
    
    def use_saved_selector(self, text):
        """Usa il selettore salvato per inserire testo"""
        if not self.saved_selector:
            self.logger.error("❌ Nessun selettore salvato")
            return False
        
        try:
            self.logger.info(f"📝 Usando selettore salvato: {self.saved_selector}")
            
            # Trova elemento con selettore salvato
            elements = self.driver.find_elements(By.CSS_SELECTOR, self.saved_selector)
            
            if not elements:
                self.logger.error(f"❌ Elemento non trovato con selettore: {self.saved_selector}")
                return False
            
            element = elements[0]
            
            if not (element.is_displayed() and element.is_enabled()):
                self.logger.error("❌ Elemento non interagibile")
                return False
            
            # Interazione
            self.logger.info("✅ Elemento trovato, inserendo testo...")
            
            # Scroll + click
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            element.click()
            time.sleep(0.3)
            
            # Clear + type
            element.clear()
            time.sleep(0.2)
            
            # Type carattere per carattere
            for char in text:
                element.send_keys(char)
                time.sleep(0.02)
            
            time.sleep(0.5)
            
            # Enter
            element.send_keys(Keys.RETURN)
            
            self.logger.info("✅ Testo inserito e Enter premuto!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Errore uso selettore salvato: {e}")
            return False
    
    def interactive_setup(self):
        """Setup interattivo"""
        print("\n🎯 CLICK & SAVE SYSTEM")
        print("=" * 50)
        
        if self.saved_selector:
            print(f"📋 Selettore salvato: {self.saved_selector}")
            choice = input("Vuoi (u)sare quello esistente o (r)iconfigurare? (u/r): ").lower()
            
            if choice == 'u':
                test_text = input("📝 Inserisci testo di test: ")
                if test_text:
                    success = self.use_saved_selector(test_text)
                    if success:
                        print("✅ Test riuscito!")
                        return self.saved_selector
                    else:
                        print("❌ Test fallito, riconfigurando...")
        
        # Nuova configurazione
        print("\n🆕 Nuova configurazione...")
        new_selector = self.setup_click_capture()
        
        if new_selector:
            print(f"\n✅ CONFIGURAZIONE COMPLETATA!")
            print(f"💾 Selettore salvato: {new_selector}")
            print("💡 Ora puoi usare questo selettore per automazioni future")
            return new_selector
        else:
            print("❌ Configurazione fallita")
            return None

# Integrazione con SoraConnectDirect
def add_click_save_to_sora():
    """Aggiungi questo metodo alla classe SoraConnectDirect"""
    
    def setup_textarea_config(self):
        """Setup configurazione textarea"""
        self.click_save = ClickSaveSystem(self.driver)
        return self.click_save.interactive_setup()
    
    def _insert_prompt_with_saved_config(self, prompt_text):
        """Inserisce prompt usando configurazione salvata"""
        try:
            # Se non abbiamo il sistema, crealo
            if not hasattr(self, 'click_save'):
                self.click_save = ClickSaveSystem(self.driver)
            
            # Prova prima con configurazione salvata
            if self.click_save.saved_selector:
                self.logger.info("📝 Tentativo con selettore salvato...")
                if self.click_save.use_saved_selector(prompt_text):
                    print(f"✅ Prompt inviato con selettore salvato!")
                    return True
                else:
                    self.logger.warning("⚠️ Selettore salvato fallito")
            
            # Se fallisce, chiedi nuova configurazione
            print("\n❌ Selettore salvato non funziona")
            choice = input("Vuoi riconfigurare? (y/n): ").lower()
            
            if choice == 'y':
                new_selector = self.click_save.setup_click_capture()
                if new_selector:
                    return self.click_save.use_saved_selector(prompt_text)
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Errore prompt con config salvata: {e}")
            return False
    
    # Restituisci i metodi da aggiungere
    return setup_textarea_config, _insert_prompt_with_saved_config

def test_click_save_system():
    """Test standalone del sistema"""
    print("🧪 TEST CLICK & SAVE SYSTEM")
    print("=" * 50)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        import requests
        import subprocess
        import time
        
        # Controlla se Edge con debug è già attivo
        debug_port = 9222
        driver = None
        
        try:
            response = requests.get(f"http://localhost:{debug_port}/json/version", timeout=5)
            if response.status_code == 200:
                print("✅ Edge con debug port trovato!")
                
                # Connetti al browser esistente
                edge_options = Options()
                edge_options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")
                
                driver = webdriver.Edge(options=edge_options)
                print(f"🔗 Connesso! URL corrente: {driver.current_url}")
                
            else:
                raise Exception("Debug port non attivo")
                
        except Exception as e:
            print("⚠️ Edge con debug non trovato, avviando nuovo browser...")
            
            # Avvia Edge con debug port
            edge_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                "msedge.exe"
            ]
            
            edge_exe = None
            for path in edge_paths:
                try:
                    if path == "msedge.exe":
                        result = subprocess.run(["where", "msedge"], 
                                              capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            edge_exe = result.stdout.strip().split('\n')[0]
                            break
                    else:
                        import os
                        if os.path.exists(path):
                            edge_exe = path
                            break
                except:
                    continue
            
            if not edge_exe:
                print("❌ Edge non trovato!")
                print("💡 Assicurati che Microsoft Edge sia installato")
                return
            
            # Chiudi Edge esistenti
            try:
                subprocess.run(["taskkill", "/f", "/im", "msedge.exe"], 
                             capture_output=True, text=True)
                time.sleep(2)
            except:
                pass
            
            # Avvia Edge con debug
            cmd = [
                edge_exe,
                f"--remote-debugging-port={debug_port}",
                "--user-data-dir=temp_edge_debug_clicksave",
                "--disable-features=VizDisplayCompositor",
                "--no-first-run",
                "--no-default-browser-check",
                "https://sora.chatgpt.com/library"
            ]
            
            print(f"🚀 Avviando Edge: {edge_exe}")
            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            print("⏳ Aspettando avvio Edge...")
            time.sleep(5)
            
            # Verifica connessione
            for attempt in range(10):
                try:
                    response = requests.get(f"http://localhost:{debug_port}/json/version", timeout=3)
                    if response.status_code == 200:
                        print("✅ Edge avviato con successo!")
                        break
                except:
                    print(f"⏳ Tentativo {attempt + 1}/10...")
                    time.sleep(2)
            else:
                print("❌ Impossibile avviare Edge con debug port")
                return
            
            # Connetti al nuovo browser
            edge_options = Options()
            edge_options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")
            
            driver = webdriver.Edge(options=edge_options)
            print("🔗 Connesso al nuovo browser!")
            
            # Vai a Sora se non ci siamo già
            if "sora.chatgpt.com" not in driver.current_url:
                print("🌐 Navigando a Sora...")
                driver.get("https://sora.chatgpt.com/library")
                time.sleep(3)
        
        # Verifica che siamo su Sora
        current_url = driver.current_url
        print(f"🔗 URL corrente: {current_url}")
        
        if "sora.chatgpt.com" not in current_url:
            print("⚠️ Non siamo su Sora, navigando...")
            driver.get("https://sora.chatgpt.com/library")
            time.sleep(3)
            print("💡 Se richiesto, fai login manualmente")
            input("⏸️ Premi Enter quando sei pronto...")
        
        # Inizializza Click & Save
        click_save = ClickSaveSystem(driver)
        
        print("\n🎯 AVVIO CONFIGURAZIONE...")
        selector = click_save.interactive_setup()
        
        if selector:
            print(f"\n🎉 SUCCESSO!")
            print(f"💾 Selettore salvato: {selector}")
            print(f"📁 File config: textarea_config.json")
            
            # Test del selettore
            test_text = "Test automatico del Click & Save system!"
            print(f"\n🧪 Test con testo: '{test_text}'")
            
            if click_save.use_saved_selector(test_text):
                print("✅ Test completato con successo!")
                print("🎉 Il sistema è pronto per l'uso!")
            else:
                print("❌ Test fallito")
        else:
            print("❌ Configurazione fallita")
        
        # Chiedi se mantenere il browser aperto
        choice = input("\n🔒 Mantenere browser aperto? (y/n): ").lower()
        if choice != 'y':
            driver.quit()
            print("👋 Browser chiuso")
        else:
            print("💡 Browser mantenuto attivo per ulteriori test")
            
    except ImportError as e:
        print(f"❌ Errore import: {e}")
        print("💡 Installa selenium: pip install selenium")
    except Exception as e:
        print(f"❌ Errore generale: {e}")
        import traceback
        traceback.print_exc()



# ------------------------
# CLI minimale
# ------------------------
def main():
    import argparse
    p = argparse.ArgumentParser(description="Registro e replay macro tastiera/mouse")
    p.add_argument("mode", choices=["record", "replay"], help="record o replay")
    p.add_argument("--file", default="actions.json", help="file JSON delle azioni")
    p.add_argument("--speed", type=float, default=1.0, help="velocità replay (2.0 = doppia)")
    args = p.parse_args()

    m = Macro(args.file)
    if args.mode == "record":
        m.record()
    else:
        m.replay(speed=args.speed)

if __name__ == "__main__":
    main()
