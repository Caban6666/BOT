import asyncio
import sqlite3
import random
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder

TOKEN = "7782978236:AAE3BTnm2KssSGPoXETj4SbFJCPv2OZKc9Y"
ADMIN_ID = 5288319146  # Замените на свой Telegram user_id

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DB Setup ---
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, media TEXT, media_type TEXT, scheduled_time TEXT)''')
conn.commit()

# --- Загрузка фиксированных шаблонов ---
TEMPLATE_REPLIES = [
    "Ты не представляешь, как приятно получать от тебя весточку 💌",
    "Спасибо, что пишешь. Это очень ценно 🌷",
    "Ты делаешь этот день чуть светлее ☀️",
    "Как же здорово, что ты рядом, хоть и по ту сторону экрана 🌸",
    "Ты умеешь согревать своей добротой даже текстом 🌼",
    "Ты настоящая находка. Не забывай об этом 🌟",
    "Спасибо за тёплые слова. Они действительно важны ❤️",
    "С тобой делиться добром — одно удовольствие 💖",
    "Ты — как лучик солнца в хмурый день 🌤",
    "Такие моменты делают жизнь светлее. Благодарю тебя 🌹"
]

# --- In-memory storage ---
user_states = {}
user_data = {}

# --- Глобальная переменная для управления автоответами ---
auto_responses_enabled = True

# --- Reply Keyboard Generators ---
def get_admin_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Добавить пост")
    kb.button(text="Список постов")
    kb.button(text="Список шаблонов")
    kb.button(text="Включить автоответы" if not auto_responses_enabled else "Отключить автоответы")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)

def get_cancel_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Отмена")
    return kb.as_markup(resize_keyboard=True)

def get_post_keyboard(post_id):
    kb = ReplyKeyboardBuilder()
    kb.button(text=f"Изменить текст {post_id}")
    kb.button(text=f"Изменить медиа {post_id}")
    kb.button(text=f"Изменить дату {post_id}")
    kb.button(text=f"Удалить пост {post_id}")
    kb.button(text="Назад")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)

def get_posts_list_keyboard():
    cursor.execute("SELECT id FROM posts")
    posts = cursor.fetchall()
    kb = ReplyKeyboardBuilder()
    for post_id, in posts:
        kb.button(text=f"Пост {post_id}")
    kb.button(text="Назад")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)

# --- Handlers ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    await message.answer("Привет! Теперь ты будешь получать тёплые послания ❤️")

@dp.message(Command("admin"))
async def admin_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())

@dp.message(F.text == "Добавить пост")
async def add_post_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    user_states[message.from_user.id] = "awaiting_text"
    await message.answer("Пришли текст сообщения (или оставь пустым, если только медиа):", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text == "Список постов")
async def list_posts_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT id, text, scheduled_time FROM posts ORDER BY scheduled_time")
    posts = cursor.fetchall()
    if not posts:
        await message.answer("Посты не найдены.", reply_markup=get_admin_keyboard())
    else:
        posts_text = "\n".join(f"{post_id}. {text} (Отправка: {scheduled_time})" for post_id, text, scheduled_time in posts)
        await message.answer(f"Текущие посты:\n{posts_text}", reply_markup=get_posts_list_keyboard())

@dp.message(F.text == "Список шаблонов")
async def list_templates_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    templates_text = "\n".join(f"{i+1}. {text}" for i, text in enumerate(TEMPLATE_REPLIES))
    await message.answer(f"Текущие шаблоны:\n{templates_text}", reply_markup=get_admin_keyboard())

@dp.message(F.text == "Отмена")
async def cancel_handler(message: types.Message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    user_data.pop(user_id, None)
    await message.answer("Действие отменено.", reply_markup=get_admin_keyboard())

@dp.message(F.text == "Включить автоответы")
async def enable_auto_responses_handler(message: types.Message):
    global auto_responses_enabled
    if message.from_user.id != ADMIN_ID:
        return
    auto_responses_enabled = True
    await message.answer("Автоответы включены ✅", reply_markup=get_admin_keyboard())

@dp.message(F.text == "Отключить автоответы")
async def disable_auto_responses_handler(message: types.Message):
    global auto_responses_enabled
    if message.from_user.id != ADMIN_ID:
        return
    auto_responses_enabled = False
    await message.answer("Автоответы отключены ❌", reply_markup=get_admin_keyboard())

@dp.message()
async def universal_handler(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state == "awaiting_text":
        user_data[user_id] = {"text": message.text or ""}
        user_states[user_id] = "awaiting_media"
        await message.answer("Теперь пришли медиа (фото/видео) или напиши 'нет', если его нет.", reply_markup=get_cancel_keyboard())
        return

    if state == "awaiting_media":
        text = user_data[user_id]["text"]
        media = None
        media_type = None
        if message.photo:
            media = message.photo[-1].file_id
            media_type = "photo"
        elif message.video:
            media = message.video.file_id
            media_type = "video"
        elif message.text.lower() == "нет":
            pass
        else:
            await message.answer("Пожалуйста, отправьте фото, видео или 'нет'", reply_markup=get_cancel_keyboard())
            return

        user_data[user_id].update({"media": media, "media_type": media_type})
        user_states[user_id] = "awaiting_date"
        await message.answer("Введите дату для отправки (например, 16.05.2025):", reply_markup=get_cancel_keyboard())
        return

    if state == "awaiting_date":
        date_str = message.text.strip()
        try:
            scheduled_date = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            await message.answer("Неверный формат даты. Пожалуйста, введите дату в формате DD.MM.YYYY (например, 16.05.2025):", reply_markup=get_cancel_keyboard())
            return

        user_data[user_id].update({"scheduled_date": scheduled_date})
        user_states[user_id] = "awaiting_time"
        await message.answer("Введите время для отправки (например, 14:30):", reply_markup=get_cancel_keyboard())
        return

    if state == "awaiting_time":
        time_str = message.text.strip()
        try:
            scheduled_time = datetime.strptime(time_str, "%H:%M")
        except ValueError:
            await message.answer("Неверный формат времени. Пожалуйста, введите время в формате HH:MM (например, 14:30):", reply_markup=get_cancel_keyboard())
            return

        scheduled_datetime = datetime.combine(user_data[user_id]["scheduled_date"], scheduled_time.time())
        if scheduled_datetime < datetime.now():
            await message.answer("Время отправки не может быть в прошлом. Пожалуйста, введите правильную дату и время.", reply_markup=get_cancel_keyboard())
            return

        data = user_data[user_id]
        cursor.execute("INSERT INTO posts (text, media, media_type, scheduled_time) VALUES (?, ?, ?, ?)",
                       (data["text"], data["media"], data["media_type"], scheduled_datetime.isoformat()))
        conn.commit()
        await message.answer(f"Пост запланирован на {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}", reply_markup=get_admin_keyboard())
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        return

    if state == "awaiting_edit_post_text":
        post_id = user_data[user_id]["post_id"]
        cursor.execute("UPDATE posts SET text = ? WHERE id = ?", (message.text, post_id))
        conn.commit()
        await message.answer("Текст поста обновлён ✅", reply_markup=get_admin_keyboard())
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        return

    if state == "awaiting_edit_post_media":
        post_id = user_data[user_id]["post_id"]
        media = None
        media_type = None
        if message.photo:
            media = message.photo[-1].file_id
            media_type = "photo"
        elif message.video:
            media = message.video.file_id
            media_type = "video"
        elif message.text.lower() == "нет":
            pass
        else:
            await message.answer("Пожалуйста, отправьте фото, видео или 'нет'", reply_markup=get_cancel_keyboard())
            return

        cursor.execute("UPDATE posts SET media = ?, media_type = ? WHERE id = ?", (media, media_type, post_id))
        conn.commit()
        await message.answer("Медиа поста обновлено ✅", reply_markup=get_admin_keyboard())
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        return

    if state == "awaiting_edit_post_date":
        post_id = user_data[user_id]["post_id"]
        date_str = message.text.strip()
        try:
            scheduled_date = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            await message.answer("Неверный формат даты. Пожалуйста, введите дату в формате DD.MM.YYYY (например, 16.05.2025):", reply_markup=get_cancel_keyboard())
            return

        user_data[user_id].update({"scheduled_date": scheduled_date})
        user_states[user_id] = "awaiting_edit_post_time"
        await message.answer("Введите время для отправки (например, 14:30):", reply_markup=get_cancel_keyboard())
        return

    if state == "awaiting_edit_post_time":
        post_id = user_data[user_id]["post_id"]
        time_str = message.text.strip()
        try:
            scheduled_time = datetime.strptime(time_str, "%H:%M")
        except ValueError:
            await message.answer("Неверный формат времени. Пожалуйста, введите время в формате HH:MM (например, 14:30):", reply_markup=get_cancel_keyboard())
            return

        scheduled_datetime = datetime.combine(user_data[user_id]["scheduled_date"], scheduled_time.time())
        if scheduled_datetime < datetime.now():
            await message.answer("Время отправки не может быть в прошлом. Пожалуйста, введите правильную дату и время.", reply_markup=get_cancel_keyboard())
            return

        cursor.execute("UPDATE posts SET scheduled_time = ? WHERE id = ?", (scheduled_datetime.isoformat(), post_id))
        conn.commit()
        await message.answer("Дата и время отправки поста обновлены ✅", reply_markup=get_admin_keyboard())
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        return

    if message.text.startswith("Пост "):
        post_id = int(message.text.split()[1])
        cursor.execute("SELECT text, media, media_type, scheduled_time FROM posts WHERE id = ?", (post_id,))
        post = cursor.fetchone()
        if post:
            text, media, media_type, scheduled_time = post
            scheduled_time_formatted = datetime.fromisoformat(scheduled_time).strftime("%d.%m.%Y %H:%M")
            media_info = f"Медиа: {'Фото' if media_type == 'photo' else 'Видео' if media_type == 'video' else 'Нет'}"
            await message.answer(f"Текущий текст поста {post_id}:\n{text}\n{media_info}\nДата и время отправки: {scheduled_time_formatted}", reply_markup=get_post_keyboard(post_id))
        else:
            await message.answer("Пост не найден.", reply_markup=get_admin_keyboard())
        return

    if message.text.startswith("Изменить текст "):
        post_id = int(message.text.split()[2])
        cursor.execute("SELECT text FROM posts WHERE id = ?", (post_id,))
        post = cursor.fetchone()
        if post:
            user_states[user_id] = "awaiting_edit_post_text"
            user_data[user_id] = {"post_id": post_id}
            await message.answer(f"Текущий текст поста {post_id}:\n{post[0]}\nВведите новый текст:", reply_markup=get_cancel_keyboard())
        else:
            await message.answer("Пост не найден.", reply_markup=get_admin_keyboard())
        return

    if message.text.startswith("Изменить медиа "):
        post_id = int(message.text.split()[2])
        user_states[user_id] = "awaiting_edit_post_media"
        user_data[user_id] = {"post_id": post_id}
        await message.answer("Пришли новое медиа (фото/видео) или напиши 'нет', если его нет:", reply_markup=get_cancel_keyboard())
        return

    if message.text.startswith("Изменить дату "):
        post_id = int(message.text.split()[2])
        user_states[user_id] = "awaiting_edit_post_date"
        user_data[user_id] = {"post_id": post_id}
        await message.answer("Введите новую дату для отправки (например, 16.05.2025):", reply_markup=get_cancel_keyboard())
        return

    if message.text.startswith("Удалить пост "):
        post_id = int(message.text.split()[2])
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        await message.answer(f"Пост {post_id} удалён ✅", reply_markup=get_admin_keyboard())
        return

    if message.text == "Назад":
        await message.answer("Возвращаемся в главное меню.", reply_markup=get_admin_keyboard())
        return

    if message.text.startswith("/"):
        return

    if auto_responses_enabled and TEMPLATE_REPLIES:
        reply = random.choice(TEMPLATE_REPLIES)
        await message.answer(reply)

# --- Job ---
async def send_scheduled_posts():
    now = datetime.now().replace(second=0, microsecond=0)
    cursor.execute("SELECT * FROM posts WHERE scheduled_time <= ?", (now.isoformat(),))
    posts = cursor.fetchall()
    if posts:
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        for post in posts:
            _, text, media, media_type, _ = post
            for user in users:
                user_id = user[0]
                try:
                    if media:
                        if media_type == "photo":
                            await bot.send_photo(user_id, photo=media, caption=text)
                        elif media_type == "video":
                            await bot.send_video(user_id, video=media, caption=text)
                    else:
                        await bot.send_message(user_id, text)
                except Exception as e:
                    print(f"Ошибка отправки пользователю {user_id}: {e}")
        cursor.execute("DELETE FROM posts WHERE scheduled_time <= ?", (now.isoformat(),))
        conn.commit()

async def scheduler_loop():
    while True:
        await send_scheduled_posts()
        await asyncio.sleep(60)

async def main():
    print("Бот запущен")
    await asyncio.gather(
        dp.start_polling(bot),
        scheduler_loop(),
    )

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())