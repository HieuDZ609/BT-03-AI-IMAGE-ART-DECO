#!/usr/bin/env python3
"""
BT-03 Notification Service - Telegram
Thành viên: B4.5 Nguyễn Văn Hiếu (24IT067)
"""
import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def send_telegram(text: str) -> bool:
    if not TOKEN or not CHAT_ID:
        print("[WARN] Chưa cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID")
        return False
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[ERROR] Gửi Telegram thất bại: {e}")
        return False

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "bt03-notify"})

@app.route("/alert", methods=["POST"])
def alert():
    data = request.get_json(silent=True) or {}
    alerts = data.get("alerts", [])
    
    if not alerts:
        # Cho phép test thủ công
        msg = data.get("message", "Test alert from BT-03")
        send_telegram(f"<b>[BT-03]</b> {msg}")
        return jsonify({"ok": True})

    for a in alerts:
        status = a.get("status", "firing").upper()
        name = a.get("labels", {}).get("alertname", "Unknown")
        summary = a.get("annotations", {}).get("summary", "")
        severity = a.get("labels", {}).get("severity", "info")
        
        icon = "🔴" if status == "FIRING" else "🟢"
        text = (
            f"{icon} <b>[BT-03 {severity.upper()}]</b>\n"
            f"<b>{name}</b> — {status}\n"
            f"{summary}\n"
            f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        )
        send_telegram(text)
    
    return jsonify({"ok": True, "processed": len(alerts)})

@app.route("/test", methods=["GET"])
def test():
    ok = send_telegram(
        f"<b>[BT-03]</b> Notification service online\n"
        f"Worker 5.1 + Monitoring — {datetime.now().strftime('%H:%M:%S')}"
    )
    return jsonify({"sent": ok})

if __name__ == "__main__":
    print("BT-03 Notify Service starting on :8089")
    # Gửi tin khởi động
    send_telegram("<b>[BT-03]</b> Notify service started (B4.5)")
    app.run(host="0.0.0.0", port=8089)