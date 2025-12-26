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

# ใช้ commands.Bot เพื่อให้รองรับทั้ง Event และ Tree (Slash Commands)
bot = commands.Bot(command_prefix="!", intents=intents)

# กำหนด Timezone UTC+8
TZ_UTC_8 = datetime.timezone(datetime.timedelta(hours=8))

@bot.event
async def on_ready():
    print(f'✅ Bot Ready as {bot.user}')
    print(f'📋 Monitoring {len(CHANNEL_MAP)} channels')
    
    # Sync Slash Commands ไปยัง Discord
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} command(s) globally.")
        print('💡 Tip: ลองพิมพ์ /sync_history ใน Discord ได้เลย')
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# --- SLASH COMMAND ZONE ---

@bot.tree.command(name="sync_history", description="ดึงประวัติแชทตั้งแต่วันที่ 1 ธ.ค. (Admin Only)")
@app_commands.checks.has_permissions(administrator=True)
async def sync_history(interaction: discord.Interaction):
    """คำสั่ง Slash Command สำหรับดึงประวัติแชท"""
    
    # ตอบกลับทันทีเพื่อให้ Discord รู้ว่าบอทรับเรื่องแล้ว (Ephemeral=True คือเห็นแค่คนกด)
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("⏳ กำลังเริ่มกระบวนการดึงข้อมูลย้อนหลัง (อาจใช้เวลานาน)...")
    
    # วันที่เริ่มดึง (1 ธ.ค. 2025)
    start_date = datetime.datetime(2025, 12, 1, tzinfo=datetime.timezone.utc)
    
    total_count = 0

    # วนลูปทุกห้อง
    for channel_id_str, webhook_url in CHANNEL_MAP.items():
        try:
            channel_id = int(channel_id_str)
            channel = bot.get_channel(channel_id)
            
            if not channel:
                print(f"⚠️ ไม่พบห้อง ID: {channel_id_str}")
                continue
            
            # ส่งข้อความแจ้งเตือนความคืบหน้า (Followup message)
            status_msg = await interaction.followup.send(f"📂 กำลังอ่านประวัติห้อง **{channel.name}**...", ephemeral=True)
            channel_count = 0
            
            # ดึงข้อความ
            async for message in channel.history(after=start_date, limit=None, oldest_first=True):
                if message.author == bot.user:
                    continue

                msg_time_utc_8 = message.created_at.astimezone(TZ_UTC_8)
                att_links = ", ".join([att.url for att in message.attachments]) if message.attachments else ""
                
                payload = {
                    "date_str": msg_time_utc_8.strftime('%Y-%m-%d'),
                    "timestamp": msg_time_utc_8.strftime('%H:%M:%S'),
                    "user": message.author.name,
                    "content": message.content,
                    "attachments": att_links
                }
                
                try:
                    requests.post(webhook_url, json=payload)
                    channel_count += 1
                    total_count += 1
                    
                    if channel_count % 10 == 0:
                        await asyncio.sleep(0.5) 
                        
                except Exception as e:
                    print(f"❌ Error sending msg {message.id}: {e}")

            # แจ้งเตือนเมื่อเสร็จห้องนั้นๆ
            await interaction.followup.send(f"✅ ห้อง **{channel.name}**: ดึงเสร็จสิ้น {channel_count} ข้อความ", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาดกับห้อง {channel_id_str}: {e}", ephemeral=True)

    await interaction.followup.send(f"🎉 **เสร็จสิ้นทั้งหมด!** ดึงข้อความรวม {total_count} ข้อความลง Sheet เรียบร้อยครับ", ephemeral=True)

# จัดการ Error กรณีคนกดไม่มีสิทธิ์
@sync_history.error
async def sync_history_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้ (ต้องเป็น Administrator เท่านั้น)", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {error}", ephemeral=True)

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
            
            payload = {
                "date_str": now_utc_8.strftime('%Y-%m-%d'),
                "timestamp": now_utc_8.strftime('%H:%M:%S'),
                "user": message.author.name,
                "content": message.content,
                "attachments": att_links
            }

            response = requests.post(target_webhook_url, json=payload)
            
            if response.status_code == 200:
                print(f"[{now_utc_8.strftime('%H:%M:%S')}] Logged Message (Time is UTC+8)")
            else:
                print(f"❌ Error Uploading: {response.text}")

        except Exception as e:
            print(f"❌ Exception: {e}")

    await bot.process_commands(message)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)