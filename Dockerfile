# ใช้ Python เวอร์ชันเล็กสุด (Slim) เพื่อความเบา
FROM python:3.9-slim

# ตั้งค่า Timezone ให้เป็นเวลาไทย (Asia/Bangkok)
# ถ้าอยากใช้ UTC ให้ลบ 2 บรรทัดนี้ออก
ENV TZ=Asia/Bangkok
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# ตั้ง Folder ทำงานใน Container
WORKDIR /app

# Copy ไฟล์ requirements ไปก่อน (เพื่อทำ Caching จะได้ build ไวๆ)
COPY requirements.txt .

# ติดตั้ง Library
RUN pip install --no-cache-dir -r requirements.txt

# Copy โค้ดทั้งหมดเข้าไป
COPY . .

# คำสั่งรันบอท (แก้ชื่อไฟล์ตรงนี้ให้ตรงกับไฟล์ Python ของคุณ)
CMD ["python", "discord_logger_multi.py"]