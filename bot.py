import os
import json
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

load_dotenv()

# --- Переменные окружения ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET")
SITE_DOMAIN = "https://mp-fix.ru"

# --- Инициализация бота и диспетчера ---
bot = Bot(token=BOT_TOKEN)
bot.set_current(bot)
dp = Dispatcher(bot)

# --- Хранилище токенов и данных пользователя ---
TOKEN_FILE = "tokens.json"
USER_DATA = {}

def save_token(telegram_id: str, token: str):
    tokens = {}
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            tokens = json.load(f)
    tokens[telegram_id] = {
        "access_token": token,
        "created_at": str(datetime.utcnow())
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def get_token(telegram_id: str):
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, "r") as f:
        tokens = json.load(f)
    return tokens.get(telegram_id)

# --- Handlers ---
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    tid = msg.from_user.id
    url = (
        "https://oauth.yandex.ru/authorize?"
        f"response_type=code&client_id={YANDEX_CLIENT_ID}"
        "&scope=metrika:read+metrika:write+metrika:offline_data"
        f"&state={tid}&redirect_uri={SITE_DOMAIN}/oauth/callback"
    )
    await msg.answer(
        "👋 Привет! Это MPFIX — сервис автоматической настройки рекламы с лендингами.\n\n"
        f"🔗 Авторизуйтесь через Яндекс по ссылке:\n{url}"
    )

@dp.message_handler(lambda m: str(m.from_user.id) in USER_DATA and USER_DATA[str(m.from_user.id)] == "awaiting_title")
async def handle_title(msg: types.Message):
    tid = str(msg.from_user.id)
    USER_DATA[tid] = {"title": msg.text}
    await msg.answer("📃 Введите описание товара")
    USER_DATA[tid]["state"] = "awaiting_description"

@dp.message_handler(lambda m: str(m.from_user.id) in USER_DATA and USER_DATA[str(m.from_user.id)].get("state") == "awaiting_description")
async def handle_description(msg: types.Message):
    tid = str(msg.from_user.id)
    USER_DATA[tid]["description"] = msg.text
    await msg.answer("🔗 Вставьте ссылку на маркетплейс (WB или OZON)")
    USER_DATA[tid]["state"] = "awaiting_link"

@dp.message_handler(lambda m: str(m.from_user.id) in USER_DATA and USER_DATA[str(m.from_user.id)].get("state") == "awaiting_link")
async def handle_link(msg: types.Message):
    tid = str(msg.from_user.id)
    USER_DATA[tid]["link"] = msg.text
    await msg.answer("📸 Теперь пришлите фотографию товара")
    USER_DATA[tid]["state"] = "awaiting_photo"

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(msg: types.Message):
    tid = str(msg.from_user.id)
    data = USER_DATA.get(tid)
    if not data or data.get("state") != "awaiting_photo":
        await msg.answer("Сначала отправьте заголовок, описание и ссылку")
        return
    # Скачиваем фото
    file = await bot.get_file(msg.photo[-1].file_id)
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    img_data = httpx.get(file_url).content
    os.makedirs("static", exist_ok=True)
    img_path = f"static/client_{tid}.jpg"
    with open(img_path, "wb") as f:
        f.write(img_data)

    # Рендер лендинга
    env = Environment(loader=FileSystemLoader("."))
    tpl = env.get_template("template.html")
    html = tpl.render(
        title=data["title"],
        description=data["description"],
        link=data["link"],
        image_url=f"/static/client_{tid}.jpg"
    )
    os.makedirs("static", exist_ok=True)
    out_path = f"static/client_{tid}.html"
    with open(out_path, "w") as f:
        f.write(html)

    await msg.answer(f"🔗 Лэндинг готов: {SITE_DOMAIN}/static/client_{tid}.html")

    # Здесь можно автоматически создать счётчик Яндекс.Метрики
    # await bot.send_message(msg.from_user.id, "📊 Создаём счётчик Метрики…")
