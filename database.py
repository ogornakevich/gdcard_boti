import sqlite3
import os
import time
import string
import secrets
from typing import Optional

DB_PATH = os.path.join("db", "cards.db")

def _ensure_db_folder():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_connection():
    _ensure_db_folder()
    return sqlite3.connect(DB_PATH, timeout=5)


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            nickname TEXT,
            last_card_time INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rarity TEXT NOT NULL,
            description TEXT,
            image_path TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_cards (
            user_id INTEGER,
            card_id INTEGER,
            PRIMARY KEY (user_id, card_id)
        )
    """)
     
    c.execute("DROP TABLE IF EXISTS promo_codes")

    c.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            used_by TEXT DEFAULT '',
            uses_left INTEGER DEFAULT 1,
            permanent BOOLEAN DEFAULT 0
        )
    """)


    # 🧩 ВСТАВ ОЦЕ СЮДИ ⬇️ одразу після створення таблиць
    try:
        c.execute("ALTER TABLE promo_codes ADD COLUMN uses_left INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # Якщо колонка вже є — нічого страшного

    conn.commit()
    conn.close()


# 🔁 Користувачі
def get_or_create_user(user_id: int, username: Optional[str]):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
    conn.close()

def set_nickname(user_id: int, nickname: str):
    conn = get_connection()
    conn.execute("UPDATE users SET nickname=? WHERE user_id=?", (nickname, user_id))
    conn.commit()
    conn.close()

def get_nickname(user_id: int) -> Optional[str]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT nickname FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_last_card_time(user_id: int) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT last_card_time FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return int(row[0]) if row and row[0] is not None else 0

def update_last_card_time(user_id: int, timestamp: Optional[int] = None):
    if timestamp is None:
        timestamp = int(time.time())
    conn = get_connection()
    conn.execute("UPDATE users SET last_card_time=? WHERE user_id=?", (timestamp, user_id))
    conn.commit()
    conn.close()

# 🔁 Картки
def get_all_cards() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, rarity, description, image_path FROM cards")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "rarity": r[2], "description": r[3], "image_path": r[4]} for r in rows]

def add_card_to_user(user_id: int, card_id: int):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO user_cards (user_id, card_id) VALUES (?, ?)", (user_id, card_id))
    conn.commit()
    conn.close()

def get_last_user_card(user_id: int) -> Optional[int]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT card_id FROM user_cards WHERE user_id = ? ORDER BY rowid DESC LIMIT 1", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_user_collection_size(user_id: int) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM user_cards WHERE user_id=?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_total_cards_count() -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_rarity_stats(rarity: str) -> tuple[int, int, float]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards WHERE rarity=?", (rarity,))
    rarity_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM cards")
    total_count = c.fetchone()[0]
    conn.close()
    percent = (rarity_count / total_count * 100) if total_count else 0.0
    return rarity_count, total_count, percent

def clear_all_cards():
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM user_cards")
    c.execute("DELETE FROM cards")
    conn.commit()
    conn.close()

def delete_card_by_id(card_id: int) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM user_cards WHERE card_id=?", (card_id,))
    c.execute("DELETE FROM cards WHERE id=?", (card_id,))
    conn.commit()
    deleted = c.rowcount > 0
    conn.close()
    return deleted

def add_card(name: str, rarity: str, description: str, image_path: str):
    conn = get_connection()
    conn.execute("INSERT INTO cards (name, rarity, description, image_path) VALUES (?, ?, ?, ?)", (name, rarity, description, image_path))
    conn.commit()
    conn.close()

# 🔁 Промокоди
def add_promo_code(code: str, permanent: bool = False):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO promo_codes (code, permanent) VALUES (?, ?)", (code, int(permanent)))
    conn.commit()
    conn.close()

def generate_promo_code(length: int = 8) -> str:
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))

def create_one_time_code(uses: int = 1) -> str:
    code = generate_promo_code()
    conn = get_connection()
    conn.execute("INSERT INTO promo_codes (code, uses_left) VALUES (?, ?)", (code, uses))
    conn.commit()
    conn.close()
    return code

def use_promo_code(user_id: int, code: str) -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT code, used_by, uses_left, permanent FROM promo_codes WHERE code=?", (code,))
    row = c.fetchone()

    if not row:
        result = "❌ Промокод не знайдено."
    else:
        code, used_by, uses_left, permanent = row
        used_list = used_by.split(",") if used_by else []

        if str(user_id) in used_list and not permanent:
            result = "❌ Ви вже використали цей промокод."
        elif uses_left <= 0:
            result = "❌ Цей промокод більше недоступний."
        else:
            used_list.append(str(user_id))
            new_used_by = ",".join(used_list)
            new_uses_left = uses_left - 1

            # ✅ оновлення promo_codes
            c.execute(
                "UPDATE promo_codes SET used_by=?, uses_left=? WHERE code=?",
                (new_used_by, new_uses_left, code)
            )

            # ✅ окреме оновлення last_card_time — в іншій функції
            conn.commit()
            conn.close()
            update_last_card_time(user_id, timestamp=0)  # ця функція відкриває власне з'єднання

            result = f"✅ Кулдаун скинуто! Залишилось активацій: {new_uses_left}"

    return result
