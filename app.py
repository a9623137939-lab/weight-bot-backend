import os
import json
import requests
from datetime import datetime, time
import pytz
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = "8251988176:AAGxBNYadM1PZiWH9TTHplCzjMaGS8dgkxE"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
TIMEZONE = pytz.timezone("Europe/Moscow")
DATA_FILE = "settings.json"

# Загружаем настройки пользователей
def load_settings():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Отправка сообщения
def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=5)
    except Exception as e:
        print("Ошибка отправки:", e)

# Эндпоинт для сохранения настроек от мини-приложения
@app.route("/sync", methods=["POST"])
def sync():
    data = request.json
    chat_id = str(data.get("chat_id"))
    if not chat_id:
        return jsonify({"error": "no chat_id"}), 400

    settings = load_settings()
    if chat_id not in settings:
        settings[chat_id] = {}
    settings[chat_id]["daily_enabled"] = data.get("dailyEnabled", False)
    settings[chat_id]["daily_time"] = data.get("dailyTime", "19:00")
    settings[chat_id]["weekly_enabled"] = data.get("weeklyEnabled", False)
    settings[chat_id]["weekly_day"] = data.get("weeklyDay", 6)
    settings[chat_id]["weekly_time"] = data.get("weeklyTime", "19:00")
    # Сохраняем также последнюю отправленную неделю, чтобы не дублировать
    settings[chat_id]["last_weekly_week"] = data.get("last_weekly_week", 0)
    save_settings(settings)

    return jsonify({"ok": True})

# Эндпоинт для проверки и отправки уведомлений (вызывается по расписанию)
@app.route("/cron", methods=["GET"])
def cron():
    now = datetime.now(TIMEZONE)
    current_time = now.strftime("%H:%M")
    current_week = now.isocalendar()[1]  # номер недели в году
    settings = load_settings()

    for chat_id, user in settings.items():
        # Ежедневное напоминание
        if user.get("daily_enabled") and user.get("daily_time") == current_time:
            send_message(chat_id, "Привет 👋 не забудь отправить новые замеры!")

        # Еженедельное напоминание о том, что пора открыть приложение для сводки
        weekly_enabled = user.get("weekly_enabled")
        if weekly_enabled:
            weekly_day = user.get("weekly_day")  # 0=пн..6=вс
            weekly_time = user.get("weekly_time")
            last_week = user.get("last_weekly_week", 0)
            # Проверяем, сегодня ли нужный день недели и время, и не отправляли ли уже на этой неделе
            if now.weekday() == weekly_day and weekly_time == current_time and last_week != current_week:
                send_message(chat_id, "📊 Настало время подвести итоги недели. Открой приложение, чтобы увидеть сводку!")
                # Обновляем номер отправленной недели
                user["last_weekly_week"] = current_week
                save_settings(settings)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)