# ตั้งค่าเมนู Sync จาก Google Sheet

ให้สั่ง Sync ประวัติแชทจาก Sheet ได้โดยไม่ต้องใช้คำสั่งใน Discord (และลดปัญหา "Application did not respond")

## 1. ฝั่งบอท (เซิร์ฟเวอร์)

ในไฟล์ `.env` เพิ่ม (ถ้าต้องการใช้ API key):

```env
SYNC_PORT=5000
SYNC_API_KEY=ใส่รหัสลับที่ต้องการ
```

- ถ้าไม่ใส่ `SYNC_API_KEY` บอทจะไม่ตรวจ API key (ใช้ได้ในเครือข่ายปิด)
- พอร์ต 5000 ต้องเปิดให้ Google Sheet เรียกได้ (ถ้ารันด้วย Docker จะ map ไว้แล้วใน docker-compose)

## 2. ฝั่ง Google Sheet

1. เปิด Sheet ที่ใช้รับ Chat Log → **Extensions** → **Apps Script**
2. แทนที่หรือรวมโค้ดทั้งหมดด้วยเนื้อหาจากไฟล์ **`GoogleSheetScript.gs`** ในโปรเจกต์นี้ (มีทั้ง `doPost` เดิม + เมนูใหม่)
3. **File** → **Project properties** → **Script properties** → เพิ่ม:

   | Property        | Value |
   |-----------------|--------|
   | `BOT_SYNC_URL` | `http://IPหรือโดเมนของเซิร์ฟเวอร์บอท:5000` (ไม่มี `/trigger-sync` ต่อท้าย) |
   | `BOT_SYNC_API_KEY` | ค่าเดียวกับ `SYNC_API_KEY` ใน `.env` (ถ้ามีใช้) |

   ตัวอย่าง: ถ้าบอทอยู่ที่ `https://myserver.com` และ proxy ไปที่พอร์ต 5000 ให้ใช้  
   `BOT_SYNC_URL` = `https://myserver.com`  
   หรือถ้าเข้าโดยตรง: `http://123.45.67.89:5000`

4. บันทึกแล้วรีเฟรชหน้า Sheet จะเห็นเมนู **Chat Log** ด้านบน

## 3. การใช้เมนู

- **Sync History (ทุกช่อง ตั้งแต่ 1 ธ.ค. ปีนี้)** – ส่งคำสั่ง sync ไปที่บอท (ข้อมูลจะทยอยเข้ามาในชีท)
- **Sync History (ระบุวันที่เริ่ม)...** – ใส่ปี/เดือน/วัน แล้ว sync ตั้งแต่วันนั้น
- **สร้างชีทวันนี้ (UTC+8)** – สร้างชีทของวันนี้ใน Sheet อย่างเดียว (ไม่เรียกบอท)

## 4. แก้ปัญหา "Application did not respond" ใน Discord

คำสั่ง `/sync_history` ถูกปรับให้รัน Sync **ในพื้นหลัง** แล้วตอบกลับทันที ดังนั้น Discord จะไม่ค้าง และจะส่งผลสรุปเมื่อ sync เสร็จในภายหลัง
