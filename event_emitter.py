from datetime import datetime
import time  # oppure: import datetime
import requests
import json
import subprocess

def emit_event(event_type: str, details: dict = None, url: str = None):
    """Invia un evento a un webhook Discord."""
    if not url:
        raise ValueError("Webhook URL mancante!")

    content_text = f"📢 **Evento:** {event_type}\n🕐 {datetime.now().strftime('%H:%M:%S')}"
    if details:
        for k, v in details.items():
            content_text += f"\n**{k}:** {v}"

    payload = {
        "content": content_text,
        "embeds": [
            {
                "title": "📡 Python Event",
                "description": f"Dettagli dell'evento: `{event_type}`",
                "color": 0x3498DB
            }
        ]
    }

    try:
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json", "User-Agent": "PythonDiscordBot"},
            data=json.dumps(payload),
            timeout=10
        )
        if resp.status_code == 204:
            print(f"✅ Evento '{event_type}' inviato con successo a Discord")
        else:
            print(f"⚠️ Errore Discord ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"❌ Errore invio evento a Discord: {e}")




def wait_for_discord_approval():
    print("🕹️ Avvio bot Discord per approvazione...")
    subprocess.run(["python", "discord_approver.py"])
    print("✅ Approvazione ricevuta, riprendo.")
