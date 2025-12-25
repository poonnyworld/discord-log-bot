import discord
from discord.ext import commands
import datetime
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

def load_channel_config():
    try:
        with open('channels.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: หาไฟล์ channels.json ไม่เจอ")
        return {}

CHANNEL_MAP = load_channel_config()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Bot Ready as {bot.user}')
    print(f'📋 Monitoring {len(CHANNEL_MAP)} channels')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    current_channel_id = str(message.channel.id)

    if current_channel_id in CHANNEL_MAP:
        try:
            target_webhook_url = CHANNEL_MAP[current_channel_id]
            
            # --- ส่วนที่แก้ไข: จัดการเวลา UTC+8 ---
            # 1. ดึงเวลาปัจจุบันเป็น UTC แท้ๆ ก่อน
            utc_now = datetime.datetime.now(datetime.timezone.utc)
            # 2. สร้าง Timezone +8
            tz_utc_8 = datetime.timezone(datetime.timedelta(hours=8))
            # 3. แปลงเวลาเป็น UTC+8
            now_utc_8 = utc_now.astimezone(tz_utc_8)
            # -----------------------------------
            
            att_links = ", ".join([att.url for att in message.attachments]) if message.attachments else ""
            
            payload = {
                "date_str": now_utc_8.strftime('%Y-%m-%d'),
                "timestamp": now_utc_8.strftime('%H:%M:%S'),
                "user": message.author.name,
                "content": message.content,
                "attachments": att_links
            }

            response = requests.post(target_webhook_url, json=payload)
            
            if response.status_code == 200:
                print(f"[{now_utc_8.strftime('%H:%M:%S')}] Logged (UTC+8)")
            else:
                print(f"❌ Error: {response.text}")

        except Exception as e:
            print(f"❌ Exception: {e}")

    await bot.process_commands(message)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)