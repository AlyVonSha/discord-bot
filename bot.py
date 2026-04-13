import discord
import requests
import feedparser
import asyncio
import os
from threading import Thread
from flask import Flask
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup

# ======================
# CONFIG
# ======================
TOKEN = os.environ.get("TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

RSS_URL = "https://nitter.net/uma_musu/rss"
NEWS_URL = "https://umamusume.jp/news/"

# ======================
# FLASK (Render Web Service fix)
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
# TRANSLATE
# ======================
def translate_text(text):
    try:
        return GoogleTranslator(source="auto", target="en").translate(text)
    except Exception as e:
        print("Translate error:", e)
        return text

# ======================
# NITTER RSS
# ======================
seen_rss = set()

async def check_rss():
    global seen_rss

    await client.wait_until_ready()

    while not client.is_closed():
        try:
            feed = feedparser.parse(RSS_URL)

            if feed.entries:
                latest = feed.entries[0]

                if latest.link not in seen_rss:
                    seen_rss.add(latest.link)

                    translated = translate_text(latest.title)
                    description = f"🇯🇵 {latest.title}\n🇬🇧 {translated}"

                    send_webhook_embed(
                        "🐴 Umamusume Nitter Update",
                        description,
                        latest.link
                    )

                    print("Nieuwe Nitter update gestuurd!")

        except Exception as e:
            print("RSS error:", e)

        await asyncio.sleep(60)

# ======================
# OFFICIAL WEBSITE NEWS
# ======================
seen_news = set()

def get_latest_news():
    try:
        response = requests.get(NEWS_URL, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        article = soup.select_one("a.news__list__item")
        if article is None:
            article = soup.select_one("li a")
        if article is None:
            return None, None

        title = article.get_text(" ", strip=True)
        link = article.get("href")

        if not link:
            return None, None

        if link.startswith("/"):
            link = "https://umamusume.jp" + link
        elif not link.startswith("http"):
            link = "https://umamusume.jp/news/" + link.lstrip("/")

        return title, link

    except Exception as e:
        print("News scrape error:", e)
        return None, None

async def check_news():
    global seen_news

    await client.wait_until_ready()

    while not client.is_closed():
        try:
            title, link = get_latest_news()

            if title and link and link not in seen_news:
                seen_news.add(link)

                translated = translate_text(title)
                description = f"🇯🇵 {title}\n🇬🇧 {translated}"

                send_webhook_embed(
                    "🐴 Umamusume Official News",
                    description,
                    link
                )

                print("Nieuwe website update gestuurd!")

        except Exception as e:
            print("News loop error:", e)

        await asyncio.sleep(300)

# ======================
# EVENTS
# ======================
@client.event
async def on_ready():
    print(f"Bot online als {client.user}")
    client.loop.create_task(check_rss())
    client.loop.create_task(check_news())

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == "!test":
        send_webhook_embed(
            "Bot Test",
            "👋 Nitter + website scraper + vertaling werkt!"
        )
        await message.channel.send("OK webhook gestuurd!")

# ======================
# RUN
# ======================
if not TOKEN:
    print("TOKEN ontbreekt! Zet hem in Render ENV variables.")
else:
    client.run(TOKEN)
