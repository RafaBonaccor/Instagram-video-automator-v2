import asyncio
import discord
from discord import app_commands
from discord.ui import Button, View
import os

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1428453836191957022  # id canale dove inviare il messaggio

# Flag condiviso per ripresa
resume_flag = asyncio.Event()
user_description = ""

class ApprovalView(View):
    def __init__(self, client):
        super().__init__(timeout=None)
        self.client = client
        self.user_input = None
    
    @discord.ui.button(label="✅ Approva", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "✅ Approvato! Ora scrivi la descrizione nel canale...",
            ephemeral=True
        )
        print("⏳ In attesa del messaggio con la descrizione...")
        # Non fare nulla qui, aspetta il messaggio nel on_message
    
    @discord.ui.button(label="❌ Rifiuta", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("❌ Rifiutato!", ephemeral=True)
        await interaction.channel.send("❌ Operazione annullata.")
        resume_flag.set()  # Riprendi comunque (con descrizione vuota)
        self.stop()

async def main():
    global user_description
    
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.messages = True
    
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"🤖 Bot connesso come {client.user}")
        
        channel = client.get_channel(CHANNEL_ID)
        view = ApprovalView(client)
        
        await channel.send(
            "**🕹️ Conferma azione automatica Canva**\nVuoi continuare con l'esecuzione?\n(Se approvi, scrivi poi il testo da usare come descrizione)",
            view=view
        )
        print("⌛ In attesa di approvazione...")
    
    @client.event
    async def on_message(message):
        global user_description
        
        # Ignora i messaggi del bot stesso
        if message.author == client.user:
            return
        
        # Controlla che il messaggio sia nel canale corretto
        if message.channel.id != CHANNEL_ID:
            return
        
        # Se ricevi un messaggio, salvalo come descrizione
        user_description = message.content
        print(f"📝 Descrizione ricevuta: {user_description}")
        
        # Salva su file
        with open("approved_description.txt", "w", encoding="utf-8") as f:
            f.write(user_description)
        
        print("✅ Descrizione salvata in approved_description.txt")
        
        # Segnala che puoi riprendere
        await message.channel.send(f"✅ Descrizione salvata:\n```{user_description}```")
        resume_flag.set()

        # Chiudi il bot dopo 1 secondo
        await asyncio.sleep(1)
        await client.close()
    
    # Connetti il bot
    await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())