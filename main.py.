import os
import json
import httpx
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from bot import dp, bot
from aiogram import types
from datetime import datetime

load_dotenv()

# ————— Переменные окружения —————
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # например "https://mp-fix.ru/webhook/ваш_токен"
TOKEN_FILE = "tokens.json"

# ————— Приложение FastAPI —————
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    # Устанавливаем вебхук в Telegram
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            json={"url": WEBHOOK_URL}
        )

@app.post("/webhook")
async def telegram_webhook(request: Request):
    body = await request.json()
    update = types.Update.to_object(body)
    await dp.process_update(update)
    return {"ok": True}

@app.get("/oauth/callback")
async def oauth_callback(request: Request):
    params = dict(request.query_params)
    chat_id = params.get("state")
    code = params.get("code")
    if not chat_id or not code:
        return {"error": "Missing code or state"}

    # Обмен кода на токен
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth.yandex.ru/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": YANDEX_CLIENT_ID,
                "client_secret": YANDEX_CLIENT_SECRET
            }
        )
        data = resp.json()
        if "access_token" in data:
            token = data["access_token"]
            # Сохраняем токен
            tokens = {}
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, "r") as f:
                    tokens = json.load(f)
            tokens[chat_id] = {
                "access_token": token,
                "created_at": str(datetime.utcnow())
            }
            with open(TOKEN_FILE, "w") as f:
                json.dump(tokens, f, indent=2)

            # Уведомляем пользователя и просим данные для лендинга
            await bot.send_message(
                int(chat_id),
                "✅ Доступ к Яндексу получен! Токен сохранён.\n\n"
                "📦 Приступим к созданию сайта. Пришлите одним сообщением:\n"
                "1. Фотографию товара\n"
                "2. Наименование\n"
                "3. Описание\n"
                "4. Ссылку на товар"
            )
            return {"status": "ok"}
        else:
            await bot.send_message(int(chat_id), "❌ Ошибка при получении токена")
            return {"error": data}

@app.get("/")
async def root():
    return {"status": "running"}

# ————— Запуск через uvicorn —————
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
