import discord
from discord.ext import commands
import datetime
import os
import json
import requests
from dotenv import load_dotenv

# 1. โหลด Token จาก .env เหมือนเดิม (เพื่อความปลอดภัย)
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# 2. โหลดไฟล์ตั้งค่าช่อง (channels.json)
def load_channel_config():
    try:
        with open('channels.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: หาไฟล์ channels.json ไม่เจอ")
        return {}

# โหลด Config เข้าตัวแปร
# รูปแบบข้อมูลจะเป็น: { "ID_ห้อง_1": "URL_1", "ID_ห้อง_2": "URL_2" }
CHANNEL_MAP = load_channel_config()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Multi-Channel Logger Ready as {bot.user}')
    print(f'📋 Monitoring {len(CHANNEL_MAP)} channels:')
    for channel_id in CHANNEL_MAP:
        print(f"   - Channel ID: {channel_id}")

@bot.event
async def on_message(message):
    # ป้องกันบอทคุยกับตัวเอง
    if message.author == bot.user:
        return

    # แปลง ID ห้องเป็น String เพื่อใช้ค้นหาใน Dictionary
    current_channel_id = str(message.channel.id)

    # 3. เช็คว่าห้องนี้ มีอยู่ในรายชื่อที่เราจะเก็บบันทึกไหม?
    if current_channel_id in CHANNEL_MAP:
        try:
            # ดึง URL ปลายทางของห้องนี้ออกมา
            target_webhook_url = CHANNEL_MAP[current_channel_id]
            
            # เตรียมข้อมูล
            now = datetime.datetime.now()
            att_links = ", ".join([att.url for att in message.attachments]) if message.attachments else ""
            
            payload = {
                "date_str": now.strftime('%Y-%m-%d'),
                "timestamp": now.strftime('%H:%M:%S'),
                "user": message.author.name,
                "content": message.content,
                "attachments": att_links
            }

            # ยิงไปที่ URL เฉพาะของห้องนั้นๆ
            response = requests.post(target_webhook_url, json=payload)
            
            if response.status_code == 200:
                print(f"[{now.strftime('%H:%M:%S')}] Logged (Ch: {message.channel.name}) -> Sheet")
            else:
                print(f"❌ Error Uploading: {response.text}")

        except Exception as e:
            print(f"❌ Exception: {e}")

    # (Optional) ถ้าห้องไม่อยู่ใน List ก็ปล่อยผ่านไป ไม่ต้องทำอะไร

    await bot.process_commands(message)

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("Error: ไม่พบ DISCORD_TOKEN ในไฟล์ .env")
    else:
        bot.run(DISCORD_TOKEN)