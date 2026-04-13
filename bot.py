import discord
import requests
import feedparser
import asyncio
import os
from threading import Thread
from flask import Flask
from googletrans import Translator

# ======================
# CONFIG
# ======================
TOKEN = os.environ.get("TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
RSS_URL = "https://nitter.net/uma_musu/rss"

# ======================
# FLASK (Render 24/7 fix)
# ======================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

Thread(target=run_web).start()

# ======================
# DISCORD BOT
# ======================
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ======================
# TRANSLATOR
# ======================
translator = Translator()

# ======================
# WEBHOOK
# ======================
def send_webhook_embed(title, description, url=None):
    if not WEBHOOK_URL:
        print("WEBHOOK_URL ontbreekt!")
        return

    data = {
        "embeds": [
            {
                "title": title,
                "description": description,
                "url": url,
                "color": 0xFF66AA,
                "footer": {
                    "text": "🐴 Umamusume JP Bot"
                }
            }
        ]
    }

    try:
        requests.post(WEBHOOK_URL, json=data, timeout=10)
    except Exception as e:
        print("Webhook error:", e)

# ======================
# RSS TRACKER (NO DUPLICATES IN RUNTIME)
# ======================
seen = set()

async def check_rss():
    global seen

    await client.wait_until_ready()

    while not client.is_closed():
        try:
            feed = feedparser.parse(RSS_URL)

            if feed.entries:
                latest = feed.entries[0]

                if latest.link not in seen:
                    seen.add(latest.link)

                    # 🔥 TRANSLATE
                    try:
                        translated = translator.translate(latest.title, dest="en").text
                    except:
                        translated = latest.title

                    description = f"🇯🇵 {latest.title}\n🇬🇧 {translated}"

                    send_webhook_embed(
                        "🐴 Umamusume Update",
                        description,
                        latest.link
                    )

                    print("Nieuwe update gestuurd!")

        except Exception as e:
            print("RSS error:", e)

        await asyncio.sleep(60)

# ======================
# EVENTS
# ======================
@client.event
async def on_ready():
    print(f"Bot online als {client.user}")
    client.loop.create_task(check_rss())

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == "!test":
        send_webhook_embed("Bot Test", "👋 Bot werkt via embed!")
        await message.channel.send("OK webhook gestuurd!")

# ======================
# RUN
# ======================
if not TOKEN:
    print("TOKEN ontbreekt! Zet hem in Render ENV variables.")
else:
    client.run(TOKEN)
