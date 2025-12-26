import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import json
import requests
import asyncio
from dotenv import load_dotenv

# โหลดค่า Config
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

# ตั้งค่า Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# กำหนด Timezone UTC+8
TZ_UTC_8 = datetime.timezone(datetime.timedelta(hours=8))

@bot.event
async def on_ready():
    print(f'✅ Bot Ready as {bot.user}')
    print(f'📋 Monitoring {len(CHANNEL_MAP)} channels')
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"❌ Failed to sync: {e}")

# --- HELPER: ฟังก์ชันส่งข้อมูลแบบ Batch ---
def send_batch_to_google(url, date_str, messages_list):
    """ส่งข้อมูลรายการข้อความไปยัง Google Sheet"""
    payload = {
        "date_str": date_str,
        "messages": messages_list
    }
    
    # ระบบ Retry 3 ครั้งถ้าส่งไม่ผ่าน
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                print(f"⚠️ Upload Failed (Attempt {attempt+1}): {response.text}")
        except Exception as e:
            print(f"⚠️ Connection Error (Attempt {attempt+1}): {e}")
        
        # รอสักนิดก่อนลองใหม่
        import time
        time.sleep(2)
        
    return False

# --- SLASH COMMAND ZONE ---

@bot.tree.command(name="sync_history", description="ดึงประวัติแชทตั้งแต่วันที่ 1 ธ.ค. (Admin Only)")
@app_commands.checks.has_permissions(administrator=True)
async def sync_history(interaction: discord.Interaction):
    
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("⏳ กำลังเริ่มกระบวนการดึงข้อมูลย้อนหลัง (ระบบ Batching)...")
    
    # วันที่เริ่มดึง (1 ธ.ค. 2024) **แก้ปีตรงนี้ถ้าต้องการ**
    start_date = datetime.datetime(2024, 12, 1, tzinfo=datetime.timezone.utc)
    
    total_count = 0

    for channel_id_str, webhook_url in CHANNEL_MAP.items():
        try:
            channel_id = int(channel_id_str)
            channel = bot.get_channel(channel_id)
            
            if not channel:
                continue
            
            await interaction.followup.send(f"📂 กำลังอ่านห้อง **{channel.name}**...", ephemeral=True)
            
            # ตัวแปรสำหรับ Batching
            batch_buffer = []
            current_batch_date = None
            channel_msg_count = 0
            
            # ดึงข้อความทั้งหมด
            async for message in channel.history(after=start_date, limit=None, oldest_first=True):
                if message.author == bot.user:
                    continue

                # แปลงเวลา
                msg_time_utc_8 = message.created_at.astimezone(TZ_UTC_8)
                msg_date_str = msg_time_utc_8.strftime('%Y-%m-%d')

                # เช็คว่าข้ามวันหรือยัง? ถ้าข้ามวันให้ส่งของเก่าออกไปก่อน
                if current_batch_date is not None and msg_date_str != current_batch_date:
                    if batch_buffer:
                        send_batch_to_google(webhook_url, current_batch_date, batch_buffer)
                        batch_buffer = [] # เคลียร์กล่อง
                
                current_batch_date = msg_date_str

                # เตรียมข้อมูลใส่กล่อง
                att_links = ", ".join([att.url for att in message.attachments]) if message.attachments else ""
                msg_data = {
                    "timestamp": msg_time_utc_8.strftime('%H:%M:%S'),
                    "user": message.author.name,
                    "content": message.content,
                    "attachments": att_links
                }
                batch_buffer.append(msg_data)
                channel_msg_count += 1
                total_count += 1

                # ถ้ากล่องเต็ม (ครบ 50 ข้อความ) ให้ส่งทันที
                if len(batch_buffer) >= 50:
                    success = send_batch_to_google(webhook_url, current_batch_date, batch_buffer)
                    if success:
                        batch_buffer = [] # เคลียร์กล่อง
                        await asyncio.sleep(1) # พักหายใจ 1 วิ
                    else:
                        print(f"❌ Critical Error: ส่งข้อมูลไม่ผ่านที่ข้อความ {message.id}")

            # จบลูปห้องนี้: ส่งเศษที่เหลือในกล่อง
            if batch_buffer:
                send_batch_to_google(webhook_url, current_batch_date, batch_buffer)

            await interaction.followup.send(f"✅ ห้อง **{channel.name}**: เสร็จสิ้น {channel_msg_count} ข้อความ", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error ห้อง {channel_id_str}: {e}", ephemeral=True)

    await interaction.followup.send(f"🎉 **เสร็จสิ้นทั้งหมด!** รวม {total_count} ข้อความ", ephemeral=True)

# --- REALTIME LOGGING ZONE ---

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    current_channel_id = str(message.channel.id)

    if current_channel_id in CHANNEL_MAP:
        try:
            target_webhook_url = CHANNEL_MAP[current_channel_id]
            
            utc_now = datetime.datetime.now(datetime.timezone.utc)
            now_utc_8 = utc_now.astimezone(TZ_UTC_8)

            att_links = ", ".join([att.url for att in message.attachments]) if message.attachments else ""
            
            # Realtime ส่งทีละ 1 เหมือนเดิม (เพราะมันไม่ได้มาทีละพัน)
            # แต่เราปรับโครงสร้างให้เข้ากับ Apps Script (ใส่ list messages)
            payload = {
                "date_str": now_utc_8.strftime('%Y-%m-%d'),
                "messages": [
                    {
                        "timestamp": now_utc_8.strftime('%H:%M:%S'),
                        "user": message.author.name,
                        "content": message.content,
                        "attachments": att_links
                    }
                ]
            }

            requests.post(target_webhook_url, json=payload)
            print(f"[{now_utc_8.strftime('%H:%M:%S')}] Logged (UTC+8)")

        except Exception as e:
            print(f"❌ Exception: {e}")

    await bot.process_commands(message)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)