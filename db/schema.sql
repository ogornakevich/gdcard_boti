-- ================================
-- USERS: гравці
-- ================================
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    nickname TEXT,
    last_card_time INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0
);

-- ================================
-- CARDS: картки (поки пусто; дані додамо пізніше)
-- rarity поки текстова, пізніше переведемо на зовнішній ключ
-- ================================
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    rarity TEXT NOT NULL,
    image_path TEXT NOT NULL
);

-- ================================
-- COLLECTION: які картки має гравець (1 запис = є хоча б 1 екземпляр)
-- пізніше додамо quantity, якщо треба дублікати
-- ================================
CREATE TABLE IF NOT EXISTS collection (
    user_id INTEGER,
    card_id INTEGER,
    PRIMARY KEY (user_id, card_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (card_id) REFERENCES cards(id)
);
