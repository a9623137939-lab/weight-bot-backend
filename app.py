import os
import json
import requests
from datetime import datetime
import pytz
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # разрешаем запросы с любых доменов

BOT_TOKEN = "8251988176:AAGxBNYadM1PZiWH9TTHplCzjMaGS8dgkxE"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
TIMEZONE = pytz.timezone("Europe/Moscow")
DATA_FILE = "settings.json"

def load_settings():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=5)
    except Exception as e:
        print("Ошибка отправки:", e)

@app.route("/sync", methods=["POST", "OPTIONS"])
def sync():
    if request.method == "OPTIONS":
        return "", 200
    data = request.json
    chat_id = str(data.get("chat_id"))
    if not chat_id:
        return jsonify({"error": "no chat_id"}), 400

    settings = load_settings()
    if chat_id not in settings:
        settings[chat_id] = {}

    if data.get("type") == "settings":
        settings[chat_id]["daily_enabled"] = data.get("dailyEnabled", False)
        settings[chat_id]["daily_time"] = data.get("dailyTime", "19:00")
        settings[chat_id]["weekly_enabled"] = data.get("weeklyEnabled", False)
        settings[chat_id]["weekly_day"] = data.get("weeklyDay", 6)
        settings[chat_id]["weekly_time"] = data.get("weeklyTime", "19:00")
        settings[chat_id]["last_weekly_week"] = data.get("last_weekly_week", 0)
        save_settings(settings)
        return jsonify({"ok": True})
    elif data.get("type") == "ping":
        return jsonify({"ok": True})
    else:
        return jsonify({"error": "unknown type"}), 400

@app.route("/cron", methods=["GET"])
def cron():
    now = datetime.now(TIMEZONE)
    current_time = now.strftime("%H:%M")
    current_week = now.isocalendar()[1]
    settings = load_settings()

    for chat_id, user in settings.items():
        if user.get("daily_enabled") and user.get("daily_time") == current_time:
            send_message(chat_id, "Привет 👋 не забудь отправить новые замеры!")
        weekly_enabled = user.get("weekly_enabled")
        if weekly_enabled:
            weekly_day = user.get("weekly_day")
            weekly_time = user.get("weekly_time")
            last_week = user.get("last_weekly_week", 0)
            if now.weekday() == weekly_day and weekly_time == current_time and last_week != current_week:
                send_message(chat_id, "📊 Настало время подвести итоги недели. Открой приложение, чтобы увидеть сводку!")
                user["last_weekly_week"] = current_week
                save_settings(settings)
    return "OK", 200

@app.route("/debug", methods=["GET"])
def debug():
    if not os.path.exists(DATA_FILE):
        return jsonify({"error": "no data yet"}), 404
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
