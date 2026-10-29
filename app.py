import os
import secrets
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

MAX_API = "https://platform-api2.max.ru"
BOT_TOKEN = os.environ.get("MAX_BOT_TOKEN", "")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
VIDEO_URL = os.environ.get(
    "VIDEO_URL",
    "https://drive.google.com/file/d/1ibGA1boWD_SFYUaoKAqytrPniOEZV5y-/view?usp=sharing",
)


def headers():
    return {"Authorization": BOT_TOKEN, "Content-Type": "application/json"}


def send_video_button(chat_id):
    payload = {
        "text": "Видео для раунда:",
        "attachments": [
            {
                "type": "inline_keyboard",
                "payload": {
                    "buttons": [[
                        {"type": "link", "text": "Открыть видео", "url": VIDEO_URL}
                    ]]
                },
            }
        ],
    }
    response = requests.post(
        f"{MAX_API}/messages",
        params={"chat_id": chat_id},
        headers=headers(),
        json=payload,
        timeout=20,
    )
    response.raise_for_status()


def subscribe_webhook():
    if not (BOT_TOKEN and PUBLIC_URL):
        return
    secret = WEBHOOK_SECRET or secrets.token_urlsafe(18)
    payload = {
        "url": f"{PUBLIC_URL}/webhook",
        "update_types": ["message_created"],
        "secret": secret,
    }
    response = requests.post(
        f"{MAX_API}/subscriptions",
        headers=headers(),
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    print("MAX webhook подключён")


@app.get("/")
def index():
    return "MAX Alibi bot is running", 200


@app.get("/health")
def health():
    return jsonify({"ok": True}), 200


@app.post("/webhook")
def webhook():
    if WEBHOOK_SECRET:
        received = request.headers.get("X-Max-Bot-Api-Secret", "")
        if not secrets.compare_digest(received, WEBHOOK_SECRET):
            return jsonify({"ok": False}), 403

    update = request.get_json(silent=True) or {}
    if update.get("update_type") != "message_created":
        return jsonify({"ok": True}), 200

    message = update.get("message") or {}
    body = message.get("body") or {}
    text = (body.get("text") or "").strip().casefold()
    chat_id = (message.get("recipient") or {}).get("chat_id")

    if text == "дуглас" and chat_id is not None:
        try:
            send_video_button(chat_id)
        except Exception as exc:
            print(f"Ошибка отправки сообщения MAX: {exc}")
            return jsonify({"ok": False}), 500

    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    subscribe_webhook()
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
