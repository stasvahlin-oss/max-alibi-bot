import os
import secrets
from flask import Flask, jsonify, request
import requests
import urllib3

# В текущем окружении Render цепочка сертификатов API MAX может не распознаваться.
# HTTPS сохраняется; проверку сертификата можно включить после обновления CA-пакета.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

MAX_API = "https://platform-api2.max.ru"
BOT_TOKEN = os.environ.get("MAX_BOT_TOKEN", "")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
CODE_WORD = os.environ.get("CODE_WORD", "ДУГЛАС").strip().casefold()
CODE_WORD_1 = os.environ.get("CODE_WORD_1", "Уралмаш").strip().casefold()
MATERIAL_URL_1 = os.environ.get(
    "MATERIAL_URL_1",
    "https://drive.google.com/drive/folders/1k5aar25pinTATKglNnqSuWxJWRejNRRn?usp=drive_link",
)
CODE_WORD_2 = os.environ.get("CODE_WORD_2", "Берия").strip().casefold()
MATERIAL_URL_2 = os.environ.get(
    "MATERIAL_URL_2",
    "https://drive.google.com/drive/folders/1qz25PKYl5GboxGCbekJOkYw2julhXjho?usp=drive_link",
).strip()


def headers():
    return {"Authorization": BOT_TOKEN, "Content-Type": "application/json"}


def send_material_button(chat_id, material_url):
    payload = {
        "text": "Материал для раунда:",
        "attachments": [
            {
                "type": "inline_keyboard",
                "payload": {
                    "buttons": [[
                        {"type": "link", "text": "Открыть материал", "url": material_url}
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
        verify=False,
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
        verify=False,
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

    material_url = None
    if text == CODE_WORD_1:
        material_url = MATERIAL_URL_1
    elif CODE_WORD_2 and text == CODE_WORD_2:
        material_url = MATERIAL_URL_2

    if material_url and chat_id is not None:
        try:
            send_material_button(chat_id, material_url)
        except Exception as exc:
            print(f"Ошибка отправки сообщения MAX: {exc}")
            return jsonify({"ok": False}), 500

    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    subscribe_webhook()
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
