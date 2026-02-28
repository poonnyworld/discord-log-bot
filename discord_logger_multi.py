import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import json
import requests
import asyncio
import threading
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SYNC_PORT = int(os.getenv('SYNC_PORT', '5000'))
SYNC_API_KEY = os.getenv('SYNC_API_KEY', '')

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

# กำหนด Timezone UTC+8
TZ_UTC_8 = datetime.timezone(datetime.timedelta(hours=8))

# ฟังก์ชันส่งข้อมูล (Helper)
def send_batch_to_google(url, date_str, messages_list):
    payload = {"date_str": date_str, "messages": messages_list}
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200: return True
        except: pass
        import time; time.sleep(2)
    return False


async def run_sync(start_date, channels_to_sync, interaction=None):
    """รัน sync ประวัติแชทส่งไป Google Sheet (เรียกได้ทั้งจาก slash command และ HTTP)"""
    date_display = start_date.strftime('%Y-%m-%d')
    total_msgs = 0
    synced_channels_list = []

    def send_followup(text):
        if interaction is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                interaction.followup.send(text, ephemeral=True),
                bot.loop
            ).result(timeout=10)
        except Exception:
            pass

    for channel_id_str, webhook_url in channels_to_sync.items():
        try:
            channel_id = int(channel_id_str)
            ch = bot.get_channel(channel_id)
            if not ch:
                continue
            if interaction:
                await interaction.followup.send(f"📂 กำลังอ่านห้อง **{ch.name}** (ID: {channel_id})...", ephemeral=True)

            batch_buffer = []
            current_batch_date = None
            channel_msg_count = 0

            async for message in ch.history(after=start_date, limit=None, oldest_first=True):
                if message.author == bot.user:
                    continue
                msg_time_utc_8 = message.created_at.astimezone(TZ_UTC_8)
                msg_date_str = msg_time_utc_8.strftime('%Y-%m-%d')
                if current_batch_date is not None and msg_date_str != current_batch_date:
                    if batch_buffer:
                        send_batch_to_google(webhook_url, current_batch_date, batch_buffer)
                        batch_buffer = []
                current_batch_date = msg_date_str
                att_links = ", ".join([att.url for att in message.attachments]) if message.attachments else ""
                msg_data = {
                    "timestamp": msg_time_utc_8.strftime('%H:%M:%S'),
                    "user": message.author.name,
                    "content": message.content,
                    "attachments": att_links
                }
                batch_buffer.append(msg_data)
                channel_msg_count += 1
                total_msgs += 1
                if len(batch_buffer) >= 50:
                    send_batch_to_google(webhook_url, current_batch_date, batch_buffer)
                    batch_buffer = []
                    await asyncio.sleep(1)

            if batch_buffer:
                send_batch_to_google(webhook_url, current_batch_date, batch_buffer)
            if channel_msg_count > 0:
                synced_channels_list.append(f"<#{channel_id}> (ID: {channel_id})")
            if interaction:
                await interaction.followup.send(f"✅ ห้อง **{ch.name}**: เสร็จสิ้น {channel_msg_count} ข้อความ", ephemeral=True)
        except Exception as e:
            if interaction:
                await interaction.followup.send(f"❌ Error ห้อง {channel_id_str}: {e}", ephemeral=True)
            else:
                print(f"❌ Sync error ห้อง {channel_id_str}: {e}")

    summary_text = (
        f"🎉 **เสร็จสิ้นทั้งหมด!**\n\n📊 **สถิติ:**\n- จำนวนข้อความรวม: {total_msgs}\n- ห้องที่ Sync สำเร็จ:\n"
        + ("\n".join([f"• {c}" for c in synced_channels_list]) if synced_channels_list else "- ไม่มีข้อมูลใหม่")
    )
    if interaction:
        await interaction.followup.send(summary_text, ephemeral=True)
    else:
        print(f"[Sync] {summary_text.replace('**', '')}")
    return total_msgs, synced_channels_list


def _run_flask(bot_loop):
    from flask import Flask, request, jsonify
    app = Flask(__name__)

    @app.route('/trigger-sync', methods=['POST', 'GET'])
    def trigger_sync():
        if SYNC_API_KEY and request.headers.get('X-API-Key') != SYNC_API_KEY:
            return jsonify({"ok": False, "error": "Invalid or missing API key"}), 403
        try:
            data = request.get_json(force=True, silent=True) or {}
            start_year = data.get('start_year')
            start_month = data.get('start_month')
            start_day = data.get('start_day')
            if start_year is not None and start_month is not None and start_day is not None:
                start_date = datetime.datetime(start_year, start_month, start_day, tzinfo=datetime.timezone.utc)
            else:
                current_year = datetime.datetime.now().year
                start_date = datetime.datetime(current_year, 12, 1, tzinfo=datetime.timezone.utc)
            future = asyncio.run_coroutine_threadsafe(
                run_sync(start_date, CHANNEL_MAP, interaction=None),
                bot_loop
            )
            # ไม่รอให้ sync จบ แค่สั่งให้รันในพื้นหลัง
            return jsonify({"ok": True, "message": "Sync started in background. Data will appear in sheets when done."})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"ok": True})

    app.run(host='0.0.0.0', port=SYNC_PORT, use_reloader=False, threaded=True)


@bot.event
async def on_ready():
    print(f'✅ Bot Ready as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"❌ Failed to sync: {e}")
    # เปิด HTTP server สำหรับให้ Sheet เรียก trigger sync
    if SYNC_PORT:
        t = threading.Thread(target=_run_flask, args=(bot.loop,), daemon=True)
        t.start()
        print(f"📡 Sync trigger: http://0.0.0.0:{SYNC_PORT}/trigger-sync")

# --- SLASH COMMAND ---

@bot.tree.command(name="sync_history", description="ดึงประวัติแชทย้อนหลัง (Admin Only)")
@app_commands.describe(
    channel="ช่องที่ต้องการ sync (ถ้าไม่ระบุจะ sync ทุกช่อง)",
    start_year="ปีที่ต้องการเริ่มดึงข้อมูล (เช่น 2026)",
    start_month="เดือนที่ต้องการเริ่มดึงข้อมูล (1-12)",
    start_day="วันที่ที่ต้องการเริ่มดึงข้อมูล (1-31)"
)
@app_commands.checks.has_permissions(administrator=True)
async def sync_history(interaction: discord.Interaction, channel: discord.TextChannel = None, start_year: int = None, start_month: int = None, start_day: int = None):
    await interaction.response.defer(ephemeral=True)

    if start_year is None or start_month is None or start_day is None:
        current_year = datetime.datetime.now().year
        start_date = datetime.datetime(current_year, 12, 1, tzinfo=datetime.timezone.utc)
        date_display = f"1 ธ.ค. {current_year}"
    else:
        try:
            start_date = datetime.datetime(start_year, start_month, start_day, tzinfo=datetime.timezone.utc)
            month_names = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
                          "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
            date_display = f"{start_day} {month_names[start_month]} {start_year}"
        except ValueError as e:
            await interaction.followup.send(f"❌ วันที่ไม่ถูกต้อง: {e}\nกรุณาระบุวันที่ที่ถูกต้อง (เช่น ปี=2026, เดือน=1, วันที่=1)", ephemeral=True)
            return

    channels_to_sync = {}
    if channel:
        channel_id_str = str(channel.id)
        if channel_id_str not in CHANNEL_MAP:
            await interaction.followup.send(f"❌ ช่อง **{channel.name}** ไม่ได้อยู่ในรายการที่ต้อง sync\nกรุณาเพิ่มช่องนี้ใน `channels.json` ก่อน", ephemeral=True)
            return
        channels_to_sync[channel_id_str] = CHANNEL_MAP[channel_id_str]
        await interaction.followup.send(f"⏳ เริ่มดึงข้อมูลย้อนหลังจากช่อง **{channel.name}** ตั้งแต่ **{date_display}** (ทำงานในพื้นหลัง)...", ephemeral=True)
    else:
        channels_to_sync = CHANNEL_MAP
        await interaction.followup.send(f"⏳ เริ่มดึงข้อมูลย้อนหลังจากทุกช่องตั้งแต่ **{date_display}** (ทำงานในพื้นหลัง)...", ephemeral=True)

    asyncio.create_task(run_sync(start_date, channels_to_sync, interaction=interaction))

@sync_history.error
async def sync_history_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ ต้องเป็น Administrator เท่านั้น", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)

# --- REALTIME ---
@bot.event
async def on_message(message):
    if message.author == bot.user: return
    current_channel_id = str(message.channel.id)
    if current_channel_id in CHANNEL_MAP:
        try:
            target_webhook_url = CHANNEL_MAP[current_channel_id]
            # ใช้เวลาจาก message.created_at แปลงเป็น UTC+8 (สอดคล้องกับ sync_history)
            msg_time_utc_8 = message.created_at.astimezone(TZ_UTC_8)
            date_str = msg_time_utc_8.strftime('%Y-%m-%d')
            att_links = ", ".join([att.url for att in message.attachments]) if message.attachments else ""
            
            payload = {
                "date_str": date_str,
                "messages": [{
                    "timestamp": msg_time_utc_8.strftime('%H:%M:%S'),
                    "user": message.author.name,
                    "content": message.content,
                    "attachments": att_links
                }]
            }
            # ใช้ retry เหมือน send_batch_to_google และตรวจ response
            ok = send_batch_to_google(target_webhook_url, date_str, payload["messages"])
            if ok:
                print(f"[{date_str} {msg_time_utc_8.strftime('%H:%M:%S')}] Logged (UTC+8)")
            else:
                print(f"❌ Failed to send to Google Sheet (date={date_str})")
        except Exception as e:
            print(f"❌ Exception: {e}")
    await bot.process_commands(message)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)