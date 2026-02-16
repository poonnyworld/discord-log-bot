# คู่มือเพิ่มช่อง Discord ใหม่

## ขั้นตอนที่ 1: หา Channel ID

### วิธีที่ 1: ใช้ Discord Desktop/Web
1. เปิด Discord Developer Mode:
   - ไปที่ User Settings (⚙️) → Advanced → เปิด Developer Mode
2. คลิกขวาที่ช่องที่ต้องการ → Copy Channel ID
3. Channel ID จะเป็นตัวเลขยาวๆ เช่น `1234567890123456789`

### วิธีที่ 2: ดูจาก URL
- URL ของช่องจะมีรูปแบบ: `https://discord.com/channels/SERVER_ID/CHANNEL_ID`
- Channel ID คือตัวเลขหลัง `/` ตัวสุดท้าย

## ขั้นตอนที่ 2: สร้าง Google Apps Script Webhook URL

### กรณี A: สร้าง Google Sheet ใหม่ (แนะนำ)

1. **สร้าง Google Sheet ใหม่**
   - ไปที่ [Google Sheets](https://sheets.google.com)
   - สร้าง Sheet ใหม่

2. **สร้าง Google Apps Script**
   - ใน Sheet ใหม่: Extensions → Apps Script
   - วางโค้ดต่อไปนี้:

```javascript
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheetName = data.date_str; 
    var sheet = ss.getSheetByName(sheetName);

    // ถ้าไม่มีชีท ให้สร้างใหม่
    if (!sheet) {
      sheet = ss.insertSheet(sheetName, 0);
      sheet.appendRow(["Timestamp (UTC+8)", "User", "Message", "Attachments"]);
      sheet.getRange("A1:D1").setFontWeight("bold").setBackground("#efefef");
      sheet.setFrozenRows(1);
      sheet.setColumnWidth(1, 150);
      sheet.setColumnWidth(3, 300);
    }

    var messages = data.messages;
    
    if (messages && messages.length > 0) {
      var rows = messages.map(function(msg) {
        return [
          msg.timestamp, 
          msg.user, 
          msg.content, 
          msg.attachments
        ];
      });
      
      sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, 4).setValues(rows);
    }
    
    return ContentService.createTextOutput("Success");

  } catch (error) {
    return ContentService.createTextOutput("Error: " + error.toString());
  }
}
```

3. **Deploy เป็น Web App**
   - คลิก Deploy → New deployment
   - เลือก Type: **Web app** (เว็บแอป)
   - ไปที่แท็บ **การกำหนดค่า** (Configuration)
   - **คำอธิบายใหม่ (New description):** (ใส่คำอธิบายหรือเว้นว่างไว้ก็ได้)
   - **Execute as (ดำเนินการในฐานะ):** เลือก **"ฉัน"** หรือ **"Me"** (จะใช้บัญชี Google ของคุณ)
   - **⚠️ สำคัญมาก: Who has access (ผู้ที่มีสิทธิเข้าถึง):** 
     - **ต้องเลือก "Anyone"** หรือ **"Anyone, even anonymous"** 
     - ❌ **ห้ามเลือก "ฉันเท่านั้น" (Only me)** เพราะ Discord bot จะไม่สามารถส่งข้อมูลมาได้
     - ถ้าเลือก "ฉันเท่านั้น" webhook จะไม่ทำงาน!
   - คลิก **"การทำให้ใช้งานได้"** (Deploy)
   - ระบบจะขออนุญาตครั้งแรก → คลิก **"อนุญาต"** (Authorize)
   - คัดลอก **Web App URL** ที่ได้ (จะมีรูปแบบ: `https://script.google.com/macros/s/.../exec`)
   - ⚠️ **หมายเหตุ:** ถ้าแก้ไขโค้ดหลังจาก Deploy แล้ว ต้อง Deploy ใหม่ (เลือก "New version" หรือสร้าง deployment ใหม่)

### กรณี B: ใช้ Google Sheet เดิม

- ใช้ Webhook URL เดิมที่มีอยู่แล้ว
- ข้อความจากช่องใหม่จะบันทึกลง Sheet เดียวกับช่องอื่น

## ขั้นตอนที่ 3: อัปเดต channels.json

เมื่อได้ Channel ID และ Webhook URL แล้ว:
- แจ้งให้ฉันทราบ แล้วฉันจะอัปเดต `channels.json` ให้อัตโนมัติ

## ขั้นตอนที่ 4: รีสตาร์ทบอท

หลังจากอัปเดต `channels.json` แล้ว:
- หยุดบอท (ถ้ากำลังรันอยู่): กด `Ctrl+C`
- รันใหม่: `python discord_logger_multi.py`
- หรือถ้าใช้ Docker: `docker-compose restart`

## การทดสอบ

1. ส่งข้อความทดสอบในช่องใหม่
2. ตรวจสอบว่า Google Sheet ได้รับข้อมูล
3. ใช้คำสั่ง `/sync_history` เพื่อดึงประวัติย้อนหลัง (ถ้าต้องการ)

## การดึงประวัติย้อนหลังด้วย `/sync_history`

คำสั่ง `/sync_history` สามารถใช้ดึงประวัติการแชทย้อนหลังได้:

### วิธีใช้:

#### 1. **Sync เฉพาะช่องที่ต้องการ (แนะนำ):**

   **ดึงประวัติช่องใหม่ตั้งแต่ 1 มกราคม 2026:**
   ```
   /sync_history channel:#ชื่อช่อง start_year:2026 start_month:1 start_day:1
   ```
   
   หรือเลือกช่องจาก dropdown menu แล้วระบุวันที่

#### 2. **Sync ทุกช่อง:**

   **ดึงประวัติทุกช่องตั้งแต่ 1 มกราคม 2026:**
   ```
   /sync_history start_year:2026 start_month:1 start_day:1
   ```

   **ดึงประวัติทุกช่องตั้งแต่ 1 ธันวาคม ปีปัจจุบัน (ค่าเริ่มต้น):**
   ```
   /sync_history
   ```
   หรือไม่ต้องระบุพารามิเตอร์ใดๆ

#### 3. **ตัวอย่างอื่นๆ:**

   - Sync เฉพาะช่องตั้งแต่ 15 กุมภาพันธ์ 2025:
     ```
     /sync_history channel:#ชื่อช่อง start_year:2025 start_month:2 start_day:15
     ```
   
   - Sync ทุกช่องตั้งแต่ 1 มกราคม 2026:
     ```
     /sync_history start_year:2026 start_month:1 start_day:1
     ```

### พารามิเตอร์:

- **channel** (ช่อง): ช่องที่ต้องการ sync (ถ้าไม่ระบุจะ sync ทุกช่อง)
- **start_year** (ปี): ปีที่ต้องการเริ่มดึงข้อมูล (เช่น 2026)
- **start_month** (เดือน): เดือนที่ต้องการเริ่มดึงข้อมูล (1-12)
- **start_day** (วันที่): วันที่ที่ต้องการเริ่มดึงข้อมูล (1-31)

### หมายเหตุสำคัญ:

- ⚠️ **ข้อมูลจะไม่ซ้ำซ้อน**: คำสั่งจะดึงเฉพาะข้อความที่สร้าง**หลังจาก**วันที่ที่ระบุเท่านั้น
  - เช่น ถ้า Sheet เดิมมีข้อมูลตั้งแต่ ธ.ค. 2025 แล้ว และใช้ `/sync_history start_year:2026 start_month:1 start_day:1`
  - จะดึงเฉพาะข้อความตั้งแต่ 1 ม.ค. 2026 เป็นต้นไป **ไม่ซ้ำกับข้อมูลเดิม**
  
- ✅ **แนะนำให้ sync เฉพาะช่องใหม่**: ใช้พารามิเตอร์ `channel` เพื่อ sync เฉพาะช่องที่ต้องการ
  - เช่น `/sync_history channel:#ชื่อช่องใหม่ start_year:2026 start_month:1 start_day:1`
  - จะ sync เฉพาะช่องใหม่เท่านั้น **ไม่กระทบ Sheet เดิม**

- ต้องมีสิทธิ์ **Administrator** ในการใช้คำสั่งนี้
- การดึงข้อมูลอาจใช้เวลานานขึ้นอยู่กับจำนวนข้อความ
- ข้อมูลจะถูกบันทึกลง Google Sheet ตาม Webhook URL ที่กำหนดไว้ใน `channels.json`
