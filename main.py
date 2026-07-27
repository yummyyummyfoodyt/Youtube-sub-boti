import os
import json
import time
import asyncio
import threading
import requests
from flask import Flask

# ============================================================
#  CONFIGURATION – Replace with your real values
# ============================================================
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = 1531330918172852297          # integer, no quotes

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

CHANNEL_1_ID = "UCmlD4znP15ddkfrNxRs5UeA"
CHANNEL_2_ID = "UCipKAyrBv0p27-p81R2wufA"

CHANNEL_1_MSG = "🎉 Someone subscribed to **{channel_name}**! They now have **{new_count}** subscribers!"
CHANNEL_2_MSG = "🔥 {channel_name} just got a new sub! Total: **{new_count}**"

CHECK_INTERVAL_MINUTES = 5
# ============================================================

DATA_FILE = "sub_counts.json"

# -------- Keep‑alive web server --------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive"

def run_webserver():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# -------- Load/save subscriber counts --------
def load_counts():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_counts(counts):
    with open(DATA_FILE, "w") as f:
        json.dump(counts, f)

# -------- Get subscriber count from YouTube API --------
def get_subscriber_count(channel_id):
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "statistics,snippet",
        "id": channel_id,
        "key": YOUTUBE_API_KEY
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "items" in data and len(data["items"]) > 0:
            item = data["items"][0]
            stats = item["statistics"]
            name = item["snippet"]["title"]
            count = int(stats.get("subscriberCount", 0))
            return name, count
        else:
            print(f"Error fetching channel {channel_id}: {data.get('error', 'Unknown error')}")
            return None, None
    except Exception as e:
        print(f"API request failed for {channel_id}: {e}")
        return None, None

# -------- Discord bot --------
import discord
intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")
    print("Starting YouTube subscriber monitor...")
    await monitor_loop()

async def monitor_loop():
    await client.wait_until_ready()
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if channel is None:
        print("ERROR: Discord channel not found. Check DISCORD_CHANNEL_ID.")
        return

    counts = load_counts()
    channels_to_check = [
        (CHANNEL_1_ID, CHANNEL_1_MSG),
        (CHANNEL_2_ID, CHANNEL_2_MSG)
    ]

    while not client.is_closed():
        for channel_id, message_template in channels_to_check:
            name, new_count = get_subscriber_count(channel_id)
            if name is None or new_count is None:
                continue

            old_count = counts.get(channel_id, new_count)

            if new_count > old_count:
                msg = message_template.format(channel_name=name, new_count=new_count)
                await channel.send(msg)
                print(f"Sent notification: {msg}")
                counts[channel_id] = new_count
                save_counts(counts)
            elif new_count < old_count:
                counts[channel_id] = new_count
                save_counts(counts)
            else:
                counts[channel_id] = new_count
                save_counts(counts)

            await asyncio.sleep(1)

        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)

# -------- Start everything --------
if __name__ == "__main__":
    threading.Thread(target=run_webserver).start()
    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("Invalid Discord bot token. Please check your token.")
