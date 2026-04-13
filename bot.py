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
        print("WEBHOOK_URL is missing!")
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
                        "🐴 Umamusume Nitter Update",
                        description,
                        latest.link
                    )

                    print("New Nitter update sent!")

        except Exception as e:
            print("RSS error:", e)

        await asyncio.sleep(60)

# ======================
# CARD IMAGE HELPERS
# ======================
def load_font(size):
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

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    font_title = load_font(34)
    font_big = load_font(26)
    font = load_font(22)
    font_small = load_font(18)

    def text_width(text, font_obj):
        bbox = draw.textbbox((0, 0), str(text), font=font_obj)
        return bbox[2] - bbox[0]

    def fit_text(text, font_obj, max_width):
        text = str(text)
        if text_width(text, font_obj) <= max_width:
            return text
        while len(text) > 1 and text_width(text + "...", font_obj) > max_width:
            text = text[:-1]
        return text + "..."

    def wrap_text(text, font_obj, max_width, max_lines=2):
        words = str(text).split()
        if not words:
            return [""]
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if text_width(test, font_obj) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
                if len(lines) >= max_lines - 1:
                    break
        if current and len(lines) < max_lines:
            lines.append(current)

        if len(lines) == max_lines and words:
            lines[-1] = fit_text(lines[-1], font_obj, max_width)

        return lines

    # outer panel
    draw.rounded_rectangle((20, 20, width - 20, height - 20), radius=18, fill=panel, outline=border, width=2)

    # ======================
    # TOP BAR
    # ======================
    top_y = 38
    stat_w = 95

    top_stats = [
        ("AFFINITY", profile.get("affinity", "") or "?", pink),
        ("G1 WINS", profile.get("g1_wins", "") or "?", green),
        ("WHITE SKILLS", profile.get("white_skills", "") or "?", gold),
    ]

    x = 40
    for label, value, color in top_stats:
        draw.text((x, top_y), str(value), font=font_big, fill=color)
        draw.text((x, top_y + 38), label, font=font_small, fill=white)
        x += stat_w

    draw.line((335, 34, 335, 100), fill=border, width=2)

    rank = profile.get("rank", "") or "?"
    score = profile.get("score", "") or "?"
    draw.rounded_rectangle((360, 32, 410, 82), radius=24, outline=gold, width=3, fill=(35, 35, 35))
    draw.text((376, 43), fit_text(rank, font, 30), font=font, fill=gold)

    draw.text((430, 40), fit_text(score, font_big, 120), font=font_big, fill=cyan)
    draw.text((430, 78), "SCORE", font=font_small, fill=white)

    # Trainer section
    trainer_label_x = 840
    trainer_name_x = 945
    trainer_box_x1 = 980
    trainer_box_x2 = 1160

    trainer_name = profile.get("name", "") or "Unknown Trainer"
    trainer_id = profile.get("trainer_id", "") or "Not set"

    draw.text((trainer_label_x, 46), "TRAINER:", font=font_small, fill=muted)
    draw.text((trainer_name_x, 42), fit_text(trainer_name, font_big, 160), font=font_big, fill=white)

    draw.rounded_rectangle((trainer_box_x1, 32, trainer_box_x2, 76), radius=10, outline=border, width=2, fill=(34, 36, 42))
    draw.text((trainer_box_x1 + 14, 44), fit_text(trainer_id, font, 150), font=font, fill=white)

    draw.line((40, 120, 1160, 120), fill=border, width=2)

    # ======================
    # LEFT COLUMN
    # ======================
    draw.ellipse((55, 145, 145, 235), fill=(45, 45, 50), outline=border, width=3)
    draw.text((78, 178), "UMA", font=font_big, fill=white)

    draw.ellipse((55, 250, 105, 300), fill=(45, 45, 50), outline=border, width=2)
    draw.ellipse((115, 250, 165, 300), fill=(45, 45, 50), outline=border, width=2)

    draw.rounded_rectangle((55, 330, 105, 390), radius=10, fill=(75, 85, 150), outline=(120, 180, 255), width=2)
    draw.text((64, 350), "SSR", font=font_small, fill=white)

    dx = 125
    for _ in range(4):
        draw.polygon([(dx, 360), (dx + 8, 352), (dx + 16, 360), (dx + 8, 368)], fill=cyan)
        dx += 22

    draw.line((205, 145, 205, 640), fill=(80, 180, 255), width=4)

    # ======================
    # RIGHT CONTENT AREA
    # ======================
    content_x = 235

    # small top pills
    pill_y = 150
    draw.rounded_rectangle((content_x, pill_y, content_x + 20, pill_y + 12), radius=6, fill=(80, 160, 255))
    draw.rounded_rectangle((content_x + 32, pill_y, content_x + 52, pill_y + 12), radius=6, fill=(80, 160, 255))

    # comment
    y = 195
    draw.text((content_x, y), "COMMENT", font=font_small, fill=lime)
    y += 34

    comment = profile.get("comment", "") or "No comment set"
    for line in wrap_text(comment, font_big, 820, max_lines=2):
        draw.text((content_x, y), line, font=font_big, fill=white)
        y += 34

    y += 20

    # profile rows
    rows = [
        ("Club", profile.get("club", "") or "Not set"),
        ("Archive Lvl", profile.get("archive_level", "") or "Not set"),
        ("Star Umamusume", profile.get("star_uma", "") or "Not set"),
        ("Career Support", profile.get("career_support", "") or "Not set"),
    ]

    label_box_x1 = content_x
    label_box_x2 = content_x + 200
    value_x = content_x + 220
    value_max_width = 600
    row_h = 34
    row_gap = 18

    for label, value in rows:
        draw.rounded_rectangle((label_box_x1, y, label_box_x2, y + row_h), radius=12, fill=(55, 57, 63))
        draw.text((label_box_x1 + 18, y + 6), label, font=font_small, fill=white)

        safe_value = fit_text(value, font, value_max_width)
        draw.text((value_x, y + 4), safe_value, font=font, fill=white)

        y += row_h + row_gap

    # footer
    draw.text((content_x, 645), f"Discord user: {profile.get('discord_name', 'Unknown')}", font=font_small, fill=muted)

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
    print(f"Bot online as {client.user}")
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
            "👋 Nitter + translation + trainer card is working!"
        )
        await message.channel.send("Webhook test sent successfully!")
        return

    if content.startswith("!register"):
        parts = content.split()

        trainer_id = None
        if len(parts) == 2:
            trainer_id = parts[1]
        elif len(parts) == 3 and parts[1].lower() == "tid":
            trainer_id = parts[2]

        if not trainer_id:
            await message.channel.send("Usage: `!register 304265005615` or `!register tid 304265005615`")
            return

        cleaned = trainer_id.replace(" ", "")
        if not cleaned.isdigit():
            await message.channel.send("❌ Trainer ID must contain digits only.")
            return

        set_profile_field(user_id, discord_name, "trainer_id", cleaned)
        await message.channel.send(f"✅ Trainer ID saved: `{cleaned}`")
        return

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
                await message.channel.send(f"Usage: `{command} value`")
                return

            set_profile_field(user_id, discord_name, field, value)
            await message.channel.send(f"✅ `{field}` saved as: **{value}**")
            return

    if content == "!profile":
        users = load_users()
        key = str(user_id)

        if key not in users:
            await message.channel.send("❌ No profile found. Use `!register 304265005615` first, then fill in your fields with `!set...` commands.")
            return

        await send_profile_card(message.channel, users[key])
        return

    if content.startswith("!tid") or content.startswith("!trainerid"):
        parts = content.split()

        if len(parts) == 1:
            users = load_users()
            key = str(user_id)

            if key not in users:
                await message.channel.send("❌ You have not registered a trainer ID yet.")
                return

            await send_profile_card(message.channel, users[key])
            return

        trainer_id = parts[1].replace(" ", "")
        if not trainer_id.isdigit():
            await message.channel.send("❌ Trainer ID must contain digits only.")
            return

        profile = find_profile_by_trainer_id(trainer_id)
        if profile:
            await send_profile_card(message.channel, profile)
        else:
            await message.channel.send(
                f"❌ No saved profile found for `{trainer_id}`.\nRegister it first with `!register {trainer_id}`."
            )
        return

# ======================
# RUN
# ======================
if not TOKEN:
    print("TOKEN is missing! Set it in your Render environment variables.")
else:
    client.run(TOKEN)
