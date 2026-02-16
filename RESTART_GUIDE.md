# คู่มือรีสตาร์ท Discord Bot ใน Docker

## สถานการณ์ที่ 1: แก้ไขโค้ด Python (`discord_logger_multi.py`)

**ต้อง rebuild image และ restart:**

```bash
cd /root/discord-log-bot
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

หรือใช้คำสั่งเดียว:
```bash
docker-compose up -d --build
```

## สถานการณ์ที่ 2: แก้ไข `channels.json` เท่านั้น

**restart อย่างเดียวก็พอ:**

```bash
cd /root/discord-log-bot
docker-compose restart
```

หรือ:
```bash
docker restart discord_log_bot
```

## ตรวจสอบ Logs

หลังจาก restart แล้ว ตรวจสอบว่า bot ทำงานปกติ:

```bash
docker-compose logs -f discord-bot
```

หรือ:
```bash
docker logs -f discord_log_bot
```

## สรุป

- ✅ **แก้ไข `channels.json`** → `docker-compose restart` หรือ `docker restart discord_log_bot`
- ✅ **แก้ไขโค้ด Python** → `docker-compose up -d --build` (rebuild + restart)
- ✅ **ตรวจสอบ logs** → `docker-compose logs -f discord-bot`
