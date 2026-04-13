import discord
import requests
import feedparser
import asyncio
import os
import json
import io
from threading import Thread
from flask import Flask
from deep_translator import GoogleTranslator
from PIL import Image, ImageDraw, ImageFont

# ======================
# CONFIG
# ======================
TOKEN = os.environ.get("TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

RSS_URL = "https://nitter.net/uma_musu/rss"
SEEN_FILE = "seen.txt"
USERS_FILE = "users.json"

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
# FILE HELPERS
# ======================
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Users load error:", e)
    return {}

def save_users(data):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Users save error:", e)

def get_or_create_user_profile(discord_user_id, discord_name):
    users = load_users()
    key = str(discord_user_id)

    if key not in users:
        users[key] = {
            "discord_name": discord_name,
            "trainer_id": "",
            "name": "",
            "rank": "",
            "score": "",
            "affinity": "",
            "g1_wins": "",
            "white_skills": "",
            "comment": "",
            "club": "",
            "archive_level": "",
            "star_uma": "",
            "career_support": ""
        }
        save_users(users)

    return users

def find_profile_by_trainer_id(trainer_id):
    users = load_users()
    for _, profile in users.items():
        if profile.get("trainer_id", "") == trainer_id:
            return profile
    return None

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
# TRANSLATE
# ======================
def translate_text(text):
    try:
        return GoogleTranslator(source="auto", target="en").translate(text)
    except Exception as e:
        print("Translate error:", e)
        return text

# ======================
# LOAD SEEN LINKS
# ======================
seen_rss = set()

if os.path.exists(SEEN_FILE):
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    seen_rss.add(line)
    except Exception as e:
        print("Seen file load error:", e)

# ======================
# NITTER RSS
# ======================
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

                    try:
                        with open(SEEN_FILE, "a", encoding="utf-8") as f:
                            f.write(latest.link + "\n")
                    except Exception as e:
                        print("Seen file write error:", e)

                    translated = translate_text(latest.title)
                    description = f"🇯🇵 {latest.title}\n🇬🇧 {translated}"

                    send_webhook_embed(
                        "🐴 Umamusume Update",
                        description,
                        latest.link
                    )

                    print("Nieuwe Nitter update gestuurd!")

        except Exception as e:
            print("RSS error:", e)

        await asyncio.sleep(60)

# ======================
# CARD IMAGE HELPERS
# ======================
def load_font(size):
    # Probeer een paar veelvoorkomende fonts; val terug op default
    candidates = [
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
        "arial.ttf"
    ]
    for font_name in candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    return ImageFont.load_default()

def draw_pill(draw, x, y, text, fill, outline=None, text_color=(255, 255, 255), font=None, padding_x=10, padding_y=6):
    if font is None:
        font = load_font(18)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    w = text_w + padding_x * 2
    h = text_h + padding_y * 2

    draw.rounded_rectangle((x, y, x + w, y + h), radius=14, fill=fill, outline=outline if outline else fill, width=2)
    draw.text((x + padding_x, y + padding_y - 1), text, font=font, fill=text_color)

    return w, h

def create_trainer_card(profile):
    width, height = 1200, 700
    bg = (20, 22, 26)
    panel = (28, 30, 35)
    border = (55, 58, 65)
    white = (245, 245, 245)
    muted = (190, 190, 190)
    lime = (160, 230, 20)
    gold = (255, 200, 40)
    cyan = (90, 190, 255)
    pink = (255, 70, 140)
    green = (90, 210, 110)
    graypill = (70, 73, 82)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    font_title = load_font(36)
    font_big = load_font(28)
    font = load_font(22)
    font_small = load_font(18)

    # main panel
    draw.rounded_rectangle((20, 20, width - 20, height - 20), radius=18, fill=panel, outline=border, width=2)

    # top stats
    draw.text((40, 40), profile.get("affinity", "0"), font=font_big, fill=pink)
    draw.text((40, 78), "AFFINITY", font=font_small, fill=white)

    draw.text((120, 40), profile.get("g1_wins", "0"), font=font_big, fill=green)
    draw.text((120, 78), "G1 WINS", font=font_small, fill=white)

    draw.text((205, 40), profile.get("white_skills", "0"), font=font_big, fill=gold)
    draw.text((205, 78), "WHITE SKILLS", font=font_small, fill=white)

    # separator
    draw.line((290, 35, 290, 95), fill=border, width=2)

    # rank + score
    rank = profile.get("rank", "?") or "?"
    score = profile.get("score", "?") or "?"
    draw.rounded_rectangle((320, 30, 370, 80), radius=24, outline=gold, width=3, fill=(35, 35, 35))
    draw.text((335, 42), rank, font=font, fill=gold)

    draw.text((390, 38), str(score), font=font_big, fill=cyan)
    draw.text((390, 78), "SCORE", font=font_small, fill=white)

    # name + trainer id
    name = profile.get("name", "") or "Unknown Trainer"
    trainer_id = profile.get("trainer_id", "") or "Not set"
    draw.text((850, 52), f"TRAINER:", font=font_small, fill=muted)
    draw.text((965, 45), name, font=font_big, fill=white)

    # trainer id box
    draw.rounded_rectangle((975, 32, 1160, 76), radius=10, outline=border, width=2, fill=(34, 36, 42))
    draw.text((995, 44), trainer_id, font=font, fill=white)

    # divider
    draw.line((40, 120, 1160, 120), fill=border, width=2)

    # left portrait placeholder
    draw.ellipse((55, 145, 145, 235), fill=(45, 45, 50), outline=border, width=3)
    draw.text((78, 178), "UMA", font=font_big, fill=white)

    # lower mini circles
    draw.ellipse((55, 250, 105, 300), fill=(45, 45, 50), outline=border, width=2)
    draw.ellipse((115, 250, 165, 300), fill=(45, 45, 50), outline=border, width=2)

    # support placeholder
    draw.rounded_rectangle((55, 330, 105, 390), radius=10, fill=(75, 85, 150), outline=(120, 180, 255), width=2)
    draw.text((64, 350), "SSR", font=font_small, fill=white)

    # diamonds placeholder
    dx = 125
    for _ in range(4):
        draw.polygon([(dx, 360), (dx + 8, 352), (dx + 16, 360), (dx + 8, 368)], fill=cyan)
        dx += 22

    # content area separators
    draw.line((210, 150, 210, 630), fill=(80, 180, 255), width=4)
    draw.line((210, 150, 210, 630), fill=(80, 180, 255), width=4)

    # top pills
    x = 235
    y = 150

    pill_items = [
        (f"{profile.get('star_uma', 'Star Uma')}", (40, 110, 180)),
        (f"{profile.get('career_support', 'Career Support')}", (45, 115, 210)),
    ]

    for text, color in pill_items:
        w, _ = draw_pill(draw, x, y, text, fill=color, outline=(120, 190, 255), font=font_small)
        x += w + 12

    y += 50

    comment = profile.get("comment", "") or "No comment set"
    # comment wraps a bit
    comment_lines = []
    words = comment.split()
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > 850:
            if line:
                comment_lines.append(line)
            line = word
        else:
            line = test
    if line:
        comment_lines.append(line)

    draw.text((235, y), "COMMENT", font=font_small, fill=lime)
    y += 30
    for line in comment_lines[:2]:
        draw.text((235, y), line, font=font, fill=white)
        y += 32

    # profile info section
    y += 15
    profile_lines = [
        ("Club", profile.get("club", "") or "Not set"),
        ("Archive Lvl", profile.get("archive_level", "") or "Not set"),
        ("Star Umamusume", profile.get("star_uma", "") or "Not set"),
        ("Career Support", profile.get("career_support", "") or "Not set"),
    ]

    for label, value in profile_lines:
        draw.rounded_rectangle((235, y, 420, y + 34), radius=12, fill=(55, 57, 63))
        draw.text((255, y + 6), label, font=font_small, fill=white)
        draw.text((440, y + 4), value, font=font, fill=white)
        y += 52

    # footer hint
    draw.text((235, 645), f"Discord user: {profile.get('discord_name', 'Unknown')}", font=font_small, fill=muted)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

# ======================
# COMMAND HELPERS
# ======================
async def send_profile_card(channel, profile):
    card = create_trainer_card(profile)
    file = discord.File(fp=card, filename="trainer_card.png")
    await channel.send(file=file)

async def send_help(channel):
    help_text = (
        "**Umamusume Bot Commands**\n\n"
        "`!test`\n"
        "`!register 304265005615`\n"
        "`!register tid 304265005615`\n"
        "`!setname John Trainer`\n"
        "`!setrank S3`\n"
        "`!setscore 251359`\n"
        "`!setaffinity 165`\n"
        "`!setg1 21`\n"
        "`!setskills 37`\n"
        "`!setcomment feet gaming | 9* stamina | 5* mile`\n"
        "`!setclub FeetLovers`\n"
        "`!setarchive 84`\n"
        "`!setstaruma Seiun Sky`\n"
        "`!setsupport Super Creek`\n"
        "`!profile`\n"
        "`!tid`\n"
        "`!tid 304265005615`"
    )
    await channel.send(help_text)

def set_profile_field(user_id, discord_name, field_name, value):
    users = get_or_create_user_profile(user_id, discord_name)
    key = str(user_id)
    users[key][field_name] = value
    users[key]["discord_name"] = discord_name
    save_users(users)

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

    content = message.content.strip()
    user_id = message.author.id
    discord_name = str(message.author)

    if content == "!helpuma":
        await send_help(message.channel)
        return

    if content == "!test":
        send_webhook_embed(
            "Bot Test",
            "👋 Nitter + vertaling + trainer card werkt!"
        )
        await message.channel.send("OK webhook gestuurd!")
        return

    # ----------------------
    # REGISTER
    # ----------------------
    if content.startswith("!register"):
        parts = content.split()

        trainer_id = None
        if len(parts) == 2:
            trainer_id = parts[1]
        elif len(parts) == 3 and parts[1].lower() == "tid":
            trainer_id = parts[2]

        if not trainer_id:
            await message.channel.send("Gebruik: `!register 304265005615` of `!register tid 304265005615`")
            return

        cleaned = trainer_id.replace(" ", "")
        if not cleaned.isdigit():
            await message.channel.send("❌ Trainer ID moet alleen cijfers bevatten.")
            return

        set_profile_field(user_id, discord_name, "trainer_id", cleaned)
        await message.channel.send(f"✅ Trainer ID opgeslagen: `{cleaned}`")
        return

    # ----------------------
    # SIMPLE SET COMMANDS
    # ----------------------
    setters = {
        "!setname": "name",
        "!setrank": "rank",
        "!setscore": "score",
        "!setaffinity": "affinity",
        "!setg1": "g1_wins",
        "!setskills": "white_skills",
        "!setcomment": "comment",
        "!setclub": "club",
        "!setarchive": "archive_level",
        "!setstaruma": "star_uma",
        "!setsupport": "career_support",
    }

    for command, field in setters.items():
        if content.startswith(command):
            value = content[len(command):].strip()
            if not value:
                await message.channel.send(f"Gebruik: `{command} waarde`")
                return

            set_profile_field(user_id, discord_name, field, value)
            await message.channel.send(f"✅ `{field}` opgeslagen: **{value}**")
            return

    # ----------------------
    # PROFILE
    # ----------------------
    if content == "!profile":
        users = load_users()
        key = str(user_id)

        if key not in users:
            await message.channel.send("❌ Je hebt nog geen profiel. Gebruik eerst `!register 304265005615` en daarna `!setname ...` enz.")
            return

        await send_profile_card(message.channel, users[key])
        return

    # ----------------------
    # TID
    # !tid -> eigen profiel
    # !tid 304265005615 -> profiel zoeken op trainer id
    # !trainerid -> alias
    # ----------------------
    if content.startswith("!tid") or content.startswith("!trainerid"):
        parts = content.split()

        if len(parts) == 1:
            users = load_users()
            key = str(user_id)

            if key not in users:
                await message.channel.send("❌ Je hebt nog geen trainer ID geregistreerd.")
                return

            await send_profile_card(message.channel, users[key])
            return

        trainer_id = parts[1].replace(" ", "")
        if not trainer_id.isdigit():
            await message.channel.send("❌ Trainer ID moet alleen cijfers bevatten.")
            return

        profile = find_profile_by_trainer_id(trainer_id)
        if profile:
            await send_profile_card(message.channel, profile)
        else:
            await message.channel.send(
                f"❌ Geen opgeslagen profiel gevonden voor `{trainer_id}`.\n"
                f"Registreer eerst met `!register {trainer_id}`."
            )
        return

# ======================
# RUN
# ======================
if not TOKEN:
    print("TOKEN ontbreekt! Zet hem in Render ENV variables.")
else:
    client.run(TOKEN)
