/**
 * Chat Log - รับข้อมูลจาก Discord Bot + เมนู Sync จาก Sheet
 * คัดลอกโค้ดนี้ไปไว้ใน Google Apps Script (Extensions > Apps Script)
 *
 * ครั้งแรก: เปิด Sheet แล้วคลิกเมนู Chat Log > ตั้งค่า BOT URL (ครั้งแรก)
 *          ใส่ URL เช่น http://143.14.200.26:5000 (ไม่ต้องมี /trigger-sync)
 */

// --- รับข้อมูลจาก Bot (Web App) ---
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheetName = data.date_str;
    var sheet = ss.getSheetByName(sheetName);

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
          msg.timestamp || "",
          msg.user || "",
          msg.content || "",
          msg.attachments || ""
        ];
      });
      var startRow = sheet.getLastRow() + 1;
      // getRange(startRow, startCol, numRows, numCols)
      sheet.getRange(startRow, 1, rows.length, 4).setValues(rows);
    }

    return ContentService.createTextOutput("Success");
  } catch (error) {
    return ContentService.createTextOutput("Error: " + error.toString());
  }
}

// --- เมนูเมื่อเปิด Sheet ---
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("Chat Log")
    .addItem("ตั้งค่า BOT URL (ครั้งแรก)", "menuSetupBotUrl")
    .addSeparator()
    .addItem("Sync History (ทุกช่อง ตั้งแต่ 1 ธ.ค. ปีนี้)", "menuSyncDefault")
    .addItem("Sync History (ระบุวันที่เริ่ม)...", "menuSyncFromDate")
    .addSeparator()
    .addItem("สร้างชีทวันนี้ (UTC+8)", "menuCreateTodaySheet")
    .addToUi();
}

// ตั้งค่า BOT URL ผ่านเมนู (ใช้แทน Project properties ใน UI ใหม่)
function menuSetupBotUrl() {
  var ui = SpreadsheetApp.getUi();
  var props = PropertiesService.getScriptProperties();
  var current = props.getProperty("BOT_SYNC_URL") || "";
  var url = ui.prompt("ใส่ URL ของบอท (เช่น http://143.14.200.26:5000)", "ไม่ต้องมี /trigger-sync ต่อท้าย", ui.ButtonSet.OK_CANCEL);
  if (url.getSelectedButton() !== ui.Button.OK) return;
  var urlVal = (url.getResponseText() || "").trim().replace(/\/trigger-sync\/?$/, "");
  if (!urlVal) {
    ui.alert("ไม่ได้ใส่ URL");
    return;
  }
  props.setProperty("BOT_SYNC_URL", urlVal);
  var key = ui.prompt("ใส่ API Key (ถ้าบอทตั้ง SYNC_API_KEY ไว้) หรือเว้นว่างแล้วกด OK", props.getProperty("BOT_SYNC_API_KEY") || "", ui.ButtonSet.OK_CANCEL);
  if (key.getSelectedButton() === ui.Button.OK) {
    props.setProperty("BOT_SYNC_API_KEY", (key.getResponseText() || "").trim());
  }
  ui.alert("บันทึกแล้ว\nBOT_SYNC_URL = " + urlVal + "\nตอนนี้ใช้เมนู Sync History ได้เลย");
}

function getSyncConfig() {
  var props = PropertiesService.getScriptProperties();
  var url = props.getProperty("BOT_SYNC_URL");
  var apiKey = props.getProperty("BOT_SYNC_API_KEY");
  return { url: url, apiKey: apiKey || "" };
}

function menuSyncDefault() {
  var config = getSyncConfig();
  if (!config.url) {
    SpreadsheetApp.getUi().alert("ยังไม่ได้ตั้งค่า URL บอท\nคลิกเมนู Chat Log > ตั้งค่า BOT URL (ครั้งแรก) แล้วใส่ URL เช่น http://143.14.200.26:5000");
    return;
  }
  triggerSync(config.url, config.apiKey, null);
}

function menuSyncFromDate() {
  var config = getSyncConfig();
  if (!config.url) {
    SpreadsheetApp.getUi().alert("ยังไม่ได้ตั้งค่า URL บอท\nคลิกเมนู Chat Log > ตั้งค่า BOT URL (ครั้งแรก) ก่อน");
    return;
  }
  var ui = SpreadsheetApp.getUi();
  var year = ui.prompt("ปี (ค.ศ.)", "เช่น 2026", ui.ButtonSet.OK_CANCEL);
  if (year.getSelectedButton() !== ui.Button.OK) return;
  var month = ui.prompt("เดือน (1-12)", "เช่น 2", ui.ButtonSet.OK_CANCEL);
  if (month.getSelectedButton() !== ui.Button.OK) return;
  var day = ui.prompt("วันที่", "เช่น 1", ui.ButtonSet.OK_CANCEL);
  if (day.getSelectedButton() !== ui.Button.OK) return;
  var y = parseInt(year.getResponseText(), 10);
  var m = parseInt(month.getResponseText(), 10);
  var d = parseInt(day.getResponseText(), 10);
  if (isNaN(y) || isNaN(m) || isNaN(d)) {
    ui.alert("กรุณาใส่ตัวเลขที่ถูกต้อง");
    return;
  }
  triggerSync(config.url, config.apiKey, { start_year: y, start_month: m, start_day: d });
}

function triggerSync(baseUrl, apiKey, body) {
  var url = baseUrl.replace(/\/$/, "") + "/trigger-sync";
  var options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(body || {}),
    muteHttpExceptions: true
  };
  if (apiKey) {
    options.headers = { "X-API-Key": apiKey };
  }
  try {
    var response = UrlFetchApp.fetch(url, options);
    var code = response.getResponseCode();
    var text = response.getContentText();
    if (code >= 200 && code < 300) {
      var msg = "ส่งคำสั่ง Sync ไปที่บอทแล้ว\nข้อมูลจะทยอยเข้ามาในชีทเมื่อบอทดึงเสร็จ (อาจใช้เวลาสักครู่)";
      try {
        var j = JSON.parse(text);
        if (j.message) msg = j.message;
      } catch (_) {}
      SpreadsheetApp.getUi().alert(msg);
    } else {
      SpreadsheetApp.getUi().alert("บอทตอบกลับผิดปกติ: " + code + "\n" + text);
    }
  } catch (err) {
    SpreadsheetApp.getUi().alert("เชื่อมต่อบอทไม่ได้: " + err.toString() + "\nตรวจสอบ BOT_SYNC_URL และว่าเซิร์ฟเวอร์บอทเปิดพอร์ต " + (baseUrl.match(/:(\d+)/) || [])[1] + " อยู่");
  }
}

function menuCreateTodaySheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var tz = "Asia/Bangkok";
  var today = Utilities.formatDate(new Date(), tz, "yyyy-MM-dd");
  var sheet = ss.getSheetByName(today);
  if (sheet) {
    SpreadsheetApp.getUi().alert("มีชีท '" + today + "' อยู่แล้ว");
    return;
  }
  sheet = ss.insertSheet(today, 0);
  sheet.appendRow(["Timestamp (UTC+8)", "User", "Message", "Attachments"]);
  sheet.getRange("A1:D1").setFontWeight("bold").setBackground("#efefef");
  sheet.setFrozenRows(1);
  sheet.setColumnWidth(1, 150);
  sheet.setColumnWidth(3, 300);
  SpreadsheetApp.getUi().alert("สร้างชีท '" + today + "' แล้ว");
}
