import discord
import requests
import feedparser
import asyncio
import os
from threading import Thread
from flask import Flask

# ======================
# CONFIG
# ======================
TOKEN = os.environ.get("TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
RSS_URL = "https://nitter.net/uma_musu/rss"

# ======================
# FLASK (Render FIX)
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
# RSS MEMORY FIX (NO DUPLICATES)
# ======================
if os.path.exists("last_entry.txt"):
    with open("last_entry.txt", "r") as f:
        last_entry = f.read().strip()
else:
    last_entry = None

async def check_rss():
    global last_entry

    await client.wait_until_ready()

    while not client.is_closed():
        try:
            feed = feedparser.parse(RSS_URL)

            if feed.entries:
                latest = feed.entries[0]

                if latest.link != last_entry:
                    last_entry = latest.link

                    send_webhook_embed(
                        "🐴 Umamusume Update",
                        latest.title,
                        latest.link
                    )

                    # SAVE LAST ENTRY (IMPORTANT FIX)
                    with open("last_entry.txt", "w") as f:
                        f.write(last_entry)

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

    if message.content == "!uma":
        await message.channel.send("🐴 UMA BOT ONLINE!")

# ======================
# RUN
# ======================
if not TOKEN:
    print("TOKEN ontbreekt! Zet hem in Render ENV variables.")
else:
    client.run(TOKEN)