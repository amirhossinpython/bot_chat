import asyncio
from datetime import datetime, timedelta
import aiosqlite
from rubpy.bot import BotClient, filters
from rubpy.bot.models import Update
from mirbit import MirBotClient
import random

bot = BotClient(token="توکن")
DB_FILE = "bot_data.db"
REQUEST_LIMIT_SECONDS = 10
MAX_CHUNK_SIZE = 4000
ADMIN_IDS = "شناسه شما"

system_prompt = """
شما یک ربات پاسخ سوالات هستی.
"""
mirbot= MirBotClient(system_prompt)


# --- ساخت جداول ---
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        # جدول کاربران
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            chat_type TEXT,
            request_count INTEGER DEFAULT 0,
            last_request TEXT,
            last_start TEXT,
            created_at TEXT
        )
        """)
        # جدول درخواست‌ها
        await db.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            message TEXT,
            response TEXT,
            time TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)
        # جدول لاگ‌ها
        await db.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            chat_id TEXT,
            sender_id TEXT,
            name TEXT,
            username TEXT,
            chat_type TEXT,
            message TEXT
        )
        """)
        await db.commit()


# --- ثبت کاربر ---
async def register_user(user_id, first_name="", last_name="", username="", chat_type="private"):
    async with aiosqlite.connect(DB_FILE) as db:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()

        if user is None:
            await db.execute("""
                INSERT INTO users (user_id, first_name, last_name, username, chat_type, request_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, first_name, last_name, username, chat_type, 0, now))
        else:
            await db.execute("UPDATE users SET last_start = ? WHERE user_id = ?", (now, user_id))

        await db.commit()


# --- ثبت لاگ ---
async def log_message(message: Update):
    sender_id = str(message.new_message.sender_id)
    chat_id = str(message.chat_id)
    text = message.new_message.text if message.new_message.text else ""
    chat_type = getattr(message, "chat_type", "unknown")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # نام و یوزرنیم
    name = getattr(message.new_message, "author_title", None) or "نامشخص"
    username = getattr(message.new_message, "author_username", None) or "ندارد"

    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT INTO logs (time, chat_id, sender_id, name, username, chat_type, message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (now, chat_id, sender_id, name, username, chat_type, text))
        await db.commit()


# --- ثبت درخواست (ورودی + خروجی) ---
async def save_request(user_id, message_text, response_text):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        INSERT INTO requests (user_id, message, response, time)
        VALUES (?, ?, ?, ?)
        """, (user_id, message_text, response_text, now))
        await db.commit()


# --- محدودیت زمانی ---
async def can_request(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT last_request FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        now = datetime.now()

        if row and row[0]:
            last_time = datetime.fromisoformat(row[0])
            if (now - last_time) < timedelta(seconds=REQUEST_LIMIT_SECONDS):
                return False

        await db.execute("UPDATE users SET last_request = ? WHERE user_id = ?", (now.isoformat(), user_id))
        await db.commit()
        return True


# --- افزایش شمارش درخواست ---
async def increment_request(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "UPDATE users SET request_count = request_count + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


# --- دریافت آمار ---
async def get_stats(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT SUM(request_count) FROM users")
        total_requests = (await cursor.fetchone())[0] or 0

        cursor = await db.execute(
            "SELECT request_count, last_start FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        user_count = row[0] if row else 0
        last_start = row[1] if row else "نامشخص"

        return total_users, total_requests, user_count, last_start


# --- API ---



# --- پاسخ چندبخشی ---
async def send_chunked_response(bot: BotClient, chat_id, waiting_msg_id, full_text):
    chunks = [full_text[i:i + MAX_CHUNK_SIZE] for i in range(0, len(full_text), MAX_CHUNK_SIZE)]
    for idx, chunk in enumerate(chunks):
        if idx == 0:
            await bot.edit_message_text(chat_id=chat_id, message_id=waiting_msg_id, text=chunk)
        else:
            await bot.send_message(chat_id=chat_id, text=chunk)
        await asyncio.sleep(0.5)


@bot.on_update(filters.commands(['start', 'help']))
async def start(bot: BotClient, message: Update):
    await log_message(message)
    user_id = str(message.chat_id)
    print(message.chat_id)
    chat = await bot.get_chat(message.chat_id)
    first_name = chat.first_name or "دوست عزیز"

    await register_user(user_id)
    text = f"""
🌹 سلام {first_name} عزیز، خوش آمدید به چت  

🤖 من یک ربات هوش مصنوعی هستم.  
کافی‌ست پیام یا پرسش خود را ارسال کنید تا پاسخ مناسب را از mirbot دریافت نمایید ✨  

📌 قوانین استفاده:
▫️ امکان ارسال تنها یک پیام در هر {REQUEST_LIMIT_SECONDS} ثانیه وجود دارد.  
▫️ برای مشاهده وضعیت حساب و آمار خود از دستور زیر استفاده کنید:  
/آمار  

با آرزوی موفقیت 🌺
"""


    

    await message.reply(text)

@bot.on_update(filters.commands(["آمار", "امار", "stats"]))
async def stats(bot: BotClient, message: Update):
    await log_message(message)
    user_id = str(message.chat_id)
    total_users, total_requests, user_count, last_start = await get_stats(user_id)

    await message.reply(
        f"📊 آمار ربات:\n"
        f"👥 کاربران: {total_users}\n"
        f"📨 پیام‌ها: {total_requests}\n\n"
        f"🧍 پیام‌های شما: {user_count}\n"
        f"🕰️ آخرین استارت: {last_start}"
    )


@bot.on_update(filters.private)
async def handle_private(bot: BotClient, message: Update):
    await log_message(message)
   
    user_id = str(message.chat_id)
    text = message.new_message.text.strip() if message.new_message.text else ""

    if not text:
        await message.reply("⚠️ لطفاً یک پیام معتبر بفرست.")
        return

    await register_user(user_id)

    if not await can_request(user_id):
        await message.reply("⏳ لطفاً چند لحظه صبر کن بعد دوباره پیام بده.")
        return
    
    if text.startswith("/") or text in ["آمار", "امار", "stats"]:
        return

    await increment_request(user_id)

    waiting_msg = await message.reply("⏳ در حال پردازش... لطفاً صبر کنید")
    
    responses = await asyncio.gather(
        mirbot.ask_gpt4(text),
        mirbot.ask_headait(text),
        return_exceptions=True
    )
    
    
    valid_responses = [r for r in responses if isinstance(r, str) and r.strip()]
    if not valid_responses:
        response = "❌ خطا در دریافت پاسخ از سرورها."
    else:
      
        response = random.choice(valid_responses)
  
    await save_request(user_id, text, response)

   
    await send_chunked_response(bot, message.chat_id, waiting_msg.message_id, response)

   




@bot.on_update(filters.group)
async def handle_group(bot: BotClient, message: Update):
    await log_message(message)
  
    user_id = str(message.chat_id)
    text = message.new_message.text.strip() if message.new_message.text else ""

    if not text:
        await message.reply("⚠️ لطفاً یک پیام معتبر بفرست.")
        return

    await register_user(user_id)

    if not await can_request(user_id):
        await message.reply("⏳ لطفاً چند لحظه صبر کن بعد دوباره پیام بده.")
        return
    
    if text.startswith("/") or text in ["آمار", "امار", "stats"]:
        return

    await increment_request(user_id)

    waiting_msg = await message.reply("⏳ در حال پردازش... لطفاً صبر کنید")
    
    responses = await asyncio.gather(
        mirbot.ask_gpt4(text),
        mirbot.ask_headait(text),
        return_exceptions=True
    )
    
    
    valid_responses = [r for r in responses if isinstance(r, str) and r.strip()]
    if not valid_responses:
        response = "❌ خطا در دریافت پاسخ از سرورها."
    else:
        # یکی از جواب‌های درست رو به صورت رندوم انتخاب می‌کنیم
        response = random.choice(valid_responses)
        print(valid_responses)
   
    await save_request(user_id, text, response)

   
    await send_chunked_response(bot, message.chat_id, waiting_msg.message_id, response)

   


async def main():
    await init_db()
    await bot.run()

asyncio.run(main())
