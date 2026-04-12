import discord
import requests
import feedparser
import asyncio
import os

# ======================
# CONFIG (Render ENV)
# ======================
TOKEN = os.environ.get("TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

RSS_URL = "https://nitter.net/uma_musu/rss"

# ======================
# DISCORD SETUP
# ======================
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# ======================
# WEBHOOK EMBED
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
# RSS TRACKER (SAFE)
# ======================
last_entry = None

async def check_rss():
    global last_entry

    await client.wait_until_ready()

    while not client.is_closed():
        try:
            feed = feedparser.parse(RSS_URL)

            if feed and feed.entries:
                latest = feed.entries[0]

                if latest.link != last_entry:
                    last_entry = latest.link

                    send_webhook_embed(
                        "🐴 Umamusume Update",
                        latest.title,
                        latest.link
                    )

                    print("Nieuwe update gestuurd!")

        except Exception as e:
            print("RSS error (ignored):", e)

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
        send_webhook_embed("Bot Test", "👋 Bot werkt!")
        await message.channel.send("OK webhook gestuurd!")

    if message.content.startswith("!log"):
        text = message.content.replace("!log", "").strip()
        send_webhook_embed("📢 Log", text)
        await message.channel.send("Geloggd!")

# ======================
# RUN BOT
# ======================
if not TOKEN:
    print("TOKEN ontbreekt in Render ENV variables!")
else:
    client.run(TOKEN)
