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


def system_stats() -> str:
    """Đọc CPU/RAM từ /proc (chạy trên host)."""
    try:
        with open('/proc/stat') as f:
            line = f.readline().split()
        idle0 = int(line[4]); total0 = sum(int(x) for x in line[1:])
        import time
        time.sleep(0.5)
        with open('/proc/stat') as f:
            line = f.readline().split()
        idle1 = int(line[4]); total1 = sum(int(x) for x in line[1:])
        dt = total1 - total0
        di = idle1 - idle0
        cpu = 0 if dt == 0 else (1 - di / dt) * 100
    except Exception:
        cpu = -1
    try:
        mem = {}
        with open('/proc/meminfo') as f:
            for ln in f:
                k, v = ln.split(':', 1)
                mem[k.strip()] = int(v.strip().split()[0])
        total = mem.get('MemTotal', 0) / 1024
        avail = mem.get('MemAvailable', mem.get('MemFree', 0)) / 1024
        used = total - avail
        ram = (used / total * 100) if total else 0
        ram_str = f"{used:.0f}/{total:.0f} MB ({ram:.0f}%)"
    except Exception:
        ram_str = "n/a"
    cpu_str = f"{cpu:.0f}%" if cpu >= 0 else "n/a"
    return f"CPU: {cpu_str} | RAM: {ram_str}"

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
        send_telegram(text + "\n" + system_stats())
    
    return jsonify({"ok": True, "processed": len(alerts)})

@app.route("/test", methods=["GET"])
def test():
    ok = send_telegram(
        f"<b>[BT-03]</b> Notification service online\n"
        f"{system_stats()}\n"
        f"Worker 5.1 + Monitoring — {datetime.now().strftime('%H:%M:%S')}"
    )
    return jsonify({"sent": ok})


@app.route("/status", methods=["GET"])
def status():
    ok = send_telegram(
        f"<b>[BT-03 STATUS]</b>\n" + system_stats() +
        f"\n<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
    )
    return jsonify({"sent": ok, "stats": system_stats()})


import threading

_last_update_id = 0

def _poll_telegram():
    global _last_update_id
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            resp = requests.get(url, params={"offset": _last_update_id + 1, "timeout": 10}, timeout=15)
            data = resp.json()
            for upd in data.get("result", []):
                _last_update_id = max(_last_update_id, upd.get("update_id", 0))
                msg = upd.get("message", {})
                text = (msg.get("text") or "").strip().lower()
                chat = msg.get("chat", {})
                cid = chat.get("id")
                if not cid:
                    continue
                if text in ("/status", "status", "/cpu", "/ram"):
                    reply = "<b>[BT-03 STATUS]</b>\n" + system_stats() + f"\n<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                 json={"chat_id": cid, "text": reply, "parse_mode": "HTML"}, timeout=10)
                elif text in ("/help", "help", "/start"):
                    reply = ("<b>[BT-03]</b> Lệnh hỗ trợ:\n"
                             "/status - xem CPU/RAM hiện tại\n"
                             "/test - gửi tin test")
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                 json={"chat_id": cid, "text": reply, "parse_mode": "HTML"}, timeout=10)
        except Exception as e:
            print(f"[POLL ERROR] {e}")
        import time
        time.sleep(2)

if TOKEN and CHAT_ID:
    threading.Thread(target=_poll_telegram, daemon=True).start()
    print("[POLL] Telegram command polling started")

if __name__ == "__main__":
    print("BT-03 Notify Service starting on :8089")
    # Gửi tin khởi động
    send_telegram("<b>[BT-03]</b> Notify service started (B4.5)")
    app.run(host="0.0.0.0", port=8089)