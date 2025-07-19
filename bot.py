import os
import time
import random
import asyncio
import logging

from dotenv import load_dotenv
from aiogram.enums import ParseMode
from database import get_nickname, get_user_collection_size, get_connection
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


from database import (
    init_db,
    get_or_create_user,
    get_nickname,
    set_nickname,
    get_last_card_time,
    update_last_card_time,
    get_all_cards,
    add_card_to_user,
    get_last_user_card,
    get_user_collection_size,
    get_total_cards_count,
    get_rarity_stats,
    add_promo_code,
    use_promo_code,
    add_card,
    delete_card_by_id
)

# 🔧 Налаштування
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5189937995")) 
COOLDOWN = 3600
BOT_USERNAME = "gd_cards_ua_bot"

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# 📬 Безпечна відповідь
async def safe_reply(message: types.Message, text: str, **kwargs):
    try:
        await message.answer(text, **kwargs)
    except Exception as e:
        print(f"⚠️ Виняток: {e}")

# 🚀 /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username

    get_or_create_user(user_id, username)
    nickname = get_nickname(user_id)

    if nickname:
        await safe_reply(message, f"👋 Привіт, {nickname}!\nОтримай свою картку: /card")
    else:
        await safe_reply(message, "👋 Вітаю! Щоб почати, введи /setname ТвійНік")

# 📝 /setname
@dp.message(Command("setname"))
async def cmd_setname(message: types.Message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2 or len(parts[1]) < 3:
        await safe_reply(message, "❌ Нік має містити щонайменше 3 символи: /setname Ім'я")
        return

    nickname = parts[1].strip()
    set_nickname(message.from_user.id, nickname)
    await safe_reply(message, f"✅ Нік встановлено: {nickname}")

# 🎁 /promo
@dp.message(Command("promo"))
async def cmd_promo(message: types.Message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await safe_reply(message, "❌ Формат: /promo КОД")
        return

    code = parts[1].strip().upper()
    user_id = message.from_user.id
    response = use_promo_code(user_id, code)
    await safe_reply(message, response)

# 🛠️ /admin
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await safe_reply(message, "⛔️ Ця команда доступна лише адміну.")
        return

    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 2:
        await safe_reply(message,
            "⚙️ Адмін-команди:\n"
            "/admin view — показати всі картки\n"
            "/admin clear ID — видалити картку за ID\n"
            "/admin add Назва Рідкість Опис ШляхДоФото"
        )
        return

    cmd = parts[1].lower()

    if cmd == "view":
        cards = get_all_cards()
        if not cards:
            await safe_reply(message, "📦 У базі немає карток.")
            return

        reply = "🗂️ Усі картки:\n"
        for c in cards:
            reply += f"🆔 ID: {c['id']}, 📛 Назва: {c['name']}, 💎 Рідкість: {c['rarity']}\n"
        await safe_reply(message, reply)

    elif cmd == "clear":
        if len(parts) < 3 or not parts[2].isdigit():
            await safe_reply(message, "❌ Формат: /admin clear ID\n(наприклад: /admin clear 5)")
            return
        card_id = int(parts[2])
        success = delete_card_by_id(card_id)
        if success:
            await safe_reply(message, f"🗑️ Картку з ID {card_id} успішно видалено.")
        else:
            await safe_reply(message, f"❌ Картку з ID {card_id} не знайдено.")

    elif cmd == "add":
        if len(parts) < 3:
            await safe_reply(message, "❌ Формат: /admin add Назва Рідкість Опис НазваФото.png")
            return

        try:
            full_args = parts[2].strip()
            all_parts = full_args.rsplit(" ", 1)
            if len(all_parts) != 2:
                raise ValueError("Невірний формат: потрібно 4 аргументи")

            text, filename = all_parts
            split_text = text.strip().split(maxsplit=2)
            if len(split_text) < 3:
                await safe_reply(message, "❌ Помилка: недостатньо аргументів для опису")
                return

            name, rarity, description = split_text
            base_path = "C:/Users/ogorn/Desktop/gdcard_bot/data/images/cards/"
            image_path = os.path.join(base_path, filename)

            if not os.path.exists(image_path):
                await safe_reply(message, f"❌ Файл не знайдено: `{image_path}`")
                return

            add_card(name, rarity, description, image_path)
            await safe_reply(message, f"✅ Додано картку: «{name}» ({rarity})")

        except Exception as e:
            await safe_reply(message, f"❌ Помилка при додаванні: {e}")



# 🃏 /card
@dp.message(Command(commands=["card", f"card@{BOT_USERNAME}"]))
async def cmd_card(message: types.Message):
    user_id = message.from_user.id
    nickname = get_nickname(user_id)

    if not nickname:
        await safe_reply(message, "❌ Спочатку зареєструйся: /start → /setname Ім'я")
        return

    now = int(time.time())
    last_time = get_last_card_time(user_id)
    if now - last_time < COOLDOWN:
        mins, secs = divmod(COOLDOWN - (now - last_time), 60)
        await safe_reply(message, f"⏳ Наступна картка через {mins} хв. {secs} сек.")
        return

    cards = get_all_cards()
    if not cards:
        await safe_reply(message, "❌ У базі немає карток.")
        return

    collection_user = get_user_collection_size(user_id)
    collection_total = get_total_cards_count()
    if collection_user >= collection_total:
        await safe_reply(message, "🏆 Ви вже зібрали всю колекцію!\nОчікуйте оновлення або використайте /promo ✨")
        return

    last_card_id = get_last_user_card(user_id)
    available_cards = [card for card in cards if card["id"] != last_card_id]

    if not available_cards:
        await safe_reply(message, "📦 Немає нової картки. Спробуйте трохи пізніше.")
        return

    weights = {
        "common": 60, "rare": 25, "super_rare": 10,
        "epic": 5, "mythic": 3, "legendary": 1, "divine": 0.2
    }
    pool = [(card, weights.get(card["rarity"], 1)) for card in available_cards]
    choices, card_weights = zip(*pool)
    card = random.choices(choices, weights=card_weights, k=1)[0]

    add_card_to_user(user_id, card["id"])
    update_last_card_time(user_id)

    rarity_count, rarity_total, rarity_percent = get_rarity_stats(card["rarity"])
    rarity_label = {
        "common": "Звичайна ⚪️",
        "rare": "Рідкісна 🟢",
        "super_rare": "Суперрідкісна 🔵",
        "epic": "Епічна 🟣",
        "mythic": "Міфічна 🔴",
        "legendary": "Легендарна 🟡",
        "divine": "Божественна ✴️"
    }

    caption = (
        f"🃏 НОВА КАРТКА 🃏\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Гравець: {nickname}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Картка: \"{card['name']}\"\n"
        f"Опис: {card['description']}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Рідкість: {rarity_label.get(card['rarity'], card['rarity'].capitalize())} "
        f"({rarity_count}/{rarity_total}) ({rarity_percent:.2f}%)\n"
        f"Очки: +1\n"
        f"Колекція: {collection_user}/{collection_total} карток\n"
        f"━━━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 Моя колекція", callback_data="collection")]
    ])

    photo = FSInputFile(card["image_path"])
    await message.answer_photo(
        photo=photo,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# /genpromo
@dp.message(Command("genpromo"))
async def cmd_genpromo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await safe_reply(message, "⛔️ Лише адміну доступно.")
        return

    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await safe_reply(message, "❌ Формат:\n/genpromo КІЛЬКІСТЬ_ВИКОРИСТАНЬ\nНапр: /genpromo 3")
        return

    count = int(parts[1])
    from database import create_one_time_code
    promo = create_one_time_code(count)
    await safe_reply(message, f"🔐 Промокод згенеровано:\n`{promo}`\nАктивацій: {count}", parse_mode="Markdown")


# /profile
@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    from database import get_nickname, get_user_collection_size, get_total_cards_count, get_last_card_time
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    user_id = message.from_user.id
    username = message.from_user.username or "без ніка"

    get_or_create_user(user_id, username)
    nickname = get_nickname(user_id) or username
    collected = get_user_collection_size(user_id)
    total_cards = get_total_cards_count()
    last_time = get_last_card_time(user_id)
    collection_points = collected
    rating = "—"
    notifications = "выкл"

    text = (
        f"👤 **Профіль гравця**\n"
        f"Нік: **{nickname}**\n"
        f"Рейтинг: {rating}\n"
        f"Карток зібрано: **{collected} / {total_cards}**\n"
        f"Очки колекції: **{collection_points}**\n"
        f"Уведомлення: {notifications}"
    )

    keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📋 Колекція", callback_data=f"collection:{user_id}")],
        [InlineKeyboardButton(text="🏆 Топ гравців", callback_data=f"top:{user_id}")],
    ]
)


    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


# 📋 Показ колекції (спільна логіка для /collection і кнопки)
async def show_collection(user_id: int, message: types.Message):
    nickname = get_nickname(user_id)
    if not nickname:
        await safe_reply(message, "❌ Спочатку зареєструйся: /start → /setname Ім'я")
        return

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT cards.name, cards.rarity
        FROM user_cards
        JOIN cards ON user_cards.card_id = cards.id
        WHERE user_cards.user_id = ?
    """, (user_id,))
    user_cards = c.fetchall()

    c.execute("SELECT rarity, COUNT(*) FROM cards GROUP BY rarity")
    total_by_rarity = dict(c.fetchall())
    conn.close()

    rarity_order = [
        ("divine", "Божественна ✴️", 15),
        ("legendary", "Легендарна 🟡", 10),
        ("mythic", "Міфічна 🔴", 7),
        ("epic", "Епічна 🟣", 5),
        ("super_rare", "Суперрідкісна 🔵", 3),
        ("rare", "Рідкісна 🟢", 2),
        ("common", "Звичайна ⚪️", 1)
    ]

    cards_by_rarity = {}
    for name, rarity in user_cards:
        cards_by_rarity.setdefault(rarity, []).append(name)

    total_cards = sum(total_by_rarity.values())
    collected_cards = len(user_cards)
    total_points = 0

    reply = f"📋 Колекція гравця **{nickname}**\n━━━━━━━━━━━━━━━━\n"


    for key, label, points_per_card in rarity_order:
        owned = cards_by_rarity.get(key, [])
        total = total_by_rarity.get(key, 0)
        points = len(owned) * points_per_card
        total_points += points

        reply += f"**{label}**: {len(owned)}/{total} карток, {points} оч.\n"
        for name in owned:
            reply += f"• {name}\n"
        reply += "\n"

    reply += f"━━━━━━━━━━━━━━━━\n"
    reply += f"🔢 Всього: {collected_cards}/{total_cards} карток\n"
    reply += f"🏅 Очки колекції: {total_points}"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back:profile:{user_id}")]
    ]
)


    try:
        await message.edit_text(reply, parse_mode="Markdown", reply_markup=keyboard)
    except Exception:
        await safe_reply(message, reply, parse_mode="Markdown", reply_markup=keyboard)



async def show_top(message: types.Message, user_id: int, edit: bool = False):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    SELECT users.user_id, users.nickname, users.username,
           COUNT(user_cards.card_id) AS card_count
    FROM user_cards
    JOIN users ON users.user_id = user_cards.user_id
    GROUP BY user_cards.user_id
""")

    players = c.fetchall()
    conn.close()

    # Розрахунок очок за кожного гравця
    def get_points(user_id):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT cards.rarity
            FROM user_cards
            JOIN cards ON user_cards.card_id = cards.id
            WHERE user_cards.user_id = ?
        """, (user_id,))
        rows = c.fetchall()
        conn.close()

        rarity_points = {
            "common": 1,
            "rare": 2,
            "super_rare": 3,
            "epic": 5,
            "mythic": 7,
            "legendary": 10,
            "divine": 15
        }

        return sum(rarity_points.get(r[0], 0) for r in rows)

    # Побудова топу
    ranked = sorted(
        [(uid, nick, uname, cards, get_points(uid)) for uid, nick, uname, cards in players],
        key=lambda x: (x[3], x[4]), reverse=True
    )

    text = f"🏆 ТОП {min(len(ranked), 10)} ГРАВЦІВ GD Cards\n────────────\n"
    medals = ["🥇", "🥈", "🥉"]

    for i, (uid, nick, uname, cards, points) in enumerate(ranked[:35], start=1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        mention = f"[{nick}](https://t.me/{uname})" if uname else f"{nick}"
        text += f"{medal} {mention} — {cards} карт, {points} очок\n"

    text += "────────────"

    keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back:profile:{user_id}")]
    ]
)



    if edit:
        try:
            await message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
        except Exception:
            await safe_reply(message, text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await safe_reply(message, text, parse_mode="Markdown", reply_markup=keyboard)
    
@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    await show_top(message, user_id=message.from_user.id)


@dp.callback_query(lambda c: c.data.startswith("top"))
async def callback_top(callback: types.CallbackQuery):
    await show_top(callback.message, user_id=callback.from_user.id, edit=True)
    await callback.answer()

    
from aiogram.exceptions import TelegramBadRequest

@dp.callback_query(lambda c: c.data.startswith("back"))
async def callback_back(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3 or parts[1] != "profile":
        return

    owner_id = int(parts[2])
    if callback.from_user.id != owner_id:
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.exceptions import TelegramBadRequest
    from database import get_nickname, get_user_collection_size, get_total_cards_count, get_last_card_time

    get_or_create_user(owner_id, callback.from_user.username or "без ніка")
    nickname = get_nickname(owner_id)
    collected = get_user_collection_size(owner_id)
    total_cards = get_total_cards_count()
    collection_points = collected
    rating = "—"
    notifications = "выкл"

    text = (
        f"👤 **Профіль гравця**\n"
        f"Нік: **{nickname}**\n"
        f"Рейтинг: {rating}\n"
        f"Карток зібрано: **{collected} / {total_cards}**\n"
        f"Очки колекції: **{collection_points}**\n"
        f"Уведомлення: {notifications}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Колекція", callback_data=f"collection:{owner_id}")],
            [InlineKeyboardButton(text="🏆 Топ гравців", callback_data=f"top:{owner_id}")],
        ]
    )

    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise

    await callback.answer()





# 🃏 Команда /collection
@dp.message(Command("collection"))
async def cmd_collection(message: types.Message):
    await show_collection(message.from_user.id, message)


# 📋 Кнопка "Колекція"
@dp.callback_query(lambda c: c.data.startswith("collection"))
async def callback_collection(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 2:
        return
    user_id = int(parts[1])
    if callback.from_user.id != user_id:
        return

    await show_collection(user_id, callback.message)
    await callback.answer()


# 🚀 Запуск бота
async def main():
    init_db()
    add_promo_code("BOOST_ME", permanent=True)  # вічний промокод
    print("✅ Бот запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())