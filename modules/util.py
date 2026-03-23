import os
import json
from datetime import datetime
import urllib.request

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ESP32_API = os.environ.get("ESP32_API")


def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("Telegram credentials not configured")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = json.dumps(
        {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    ).encode("utf-8")

    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            if result.get("ok"):
                log("Telegram message sent successfully")
                return True
            else:
                log(f"Telegram API error: {result}")
                return False
    except Exception as e:
        log(f"Error sending Telegram message: {str(e)}")
        return False


def send_esp32(message, post_id=None, feed_id=None):
    if not ESP32_API:
        log("ESP32 API not configured")
        return None
    if not post_id and not feed_id:
        log("PostID and FeedID both None")
        return None

    try:
        url = ""
        if post_id:
            url = f"{ESP32_API}/api/post/{post_id}"
        else:
            url = f"{ESP32_API}/api/feed/{feed_id}"

        data = json.dumps({"data": message}).encode("utf-8")

        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())

            if result.get("post_id"):
                log(f"ESP32 message sent successfully")
                return result.get("post_id")
            else:
                log(f"ESP32 API error: {result}")
                return None

    except Exception as e:
        log(f"Error sending ESP32 message: {str(e)}")
        return -1
