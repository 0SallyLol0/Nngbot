import logging
import sqlite3
import secrets
import string
import time
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация бота
BOT_TOKEN = "8573486968:AAE6K4AtMQFk3XLQycIbyHRTuFDT7tAe8U4"
ADMIN_CHAT_ID = -1001998740536
SUPER_ADMIN_ID = 2086578645

# Время запуска бота
BOT_START_TIME = None
uptime_messages = {}
user_cooldowns = {}

# Система уровней и опыта
LEVEL_SYSTEM = {
    1: 300, 2: 500, 3: 700, 4: 1000, 5: 1500,
    6: 2000, 7: 2500, 8: 3000, 9: 3500, 10: 5000,
    11: 6000, 12: 7000, 13: 8000, 14: 9000, 15: 10000,
    16: 15000, 17: 20000, 18: 25000, 19: 30000, 20: 50000,
    21: 60000, 22: 70000, 23: 80000, 24: 90000, 25: 100000
}

CLASS_BASE_STATS = {
    "Воин": {
        "health": 140,
        "mana": 62.5,
        "strength": 14,
        "speed": 12,
        "agility": 11,
        "control": 5,
        "fire_affinity": 0.001,
        "water_affinity": 0.001,
        "air_affinity": 0.001,
        "earth_affinity": 0.050,
        "dark_affinity": 0.0001,
        "light_affinity": 0.0001,
        "life_affinity": 0.0001,
        "death_affinity": 0.00001
    },
    "Танк": {
        "health": 180,
        "mana": 62.5,
        "strength": 18,
        "speed": 8,
        "agility": 14,
        "control": 5,
        "fire_affinity": 0.001,
        "water_affinity": 0.001,
        "air_affinity": 0.001,
        "earth_affinity": 0.100,
        "dark_affinity": 0.0001,
        "light_affinity": 0.0001,
        "life_affinity": 0.0001,
        "death_affinity": 0.00001
    },
    "Маг атакующего класса": {
        "health": 80,
        "mana": 500,
        "strength": 8,
        "speed": 10,
        "agility": 9,
        "control": 40,
        "fire_affinity": 0.300,
        "water_affinity": 0.100,
        "air_affinity": 0.200,
        "earth_affinity": 0.150,
        "dark_affinity": 0.002,
        "light_affinity": 0.004,
        "life_affinity": 0.004,
        "death_affinity": 0.0001
    },
    "Маг поддержки": {
        "health": 70,
        "mana": 562.5,
        "strength": 7,
        "speed": 10,
        "agility": 10,
        "control": 45,
        "fire_affinity": 0.050,
        "water_affinity": 0.150,
        "air_affinity": 0.050,
        "earth_affinity": 0.050,
        "dark_affinity": 0.001,
        "light_affinity": 0.200,
        "life_affinity": 0.400,
        "death_affinity": 0.0001
    },
    "Ассасин": {
        "health": 90,
        "mana": 75,
        "strength": 9,
        "speed": 18,
        "agility": 16,
        "control": 6,
        "fire_affinity": 0.001,
        "water_affinity": 0.001,
        "air_affinity": 0.100,
        "earth_affinity": 0.001,
        "dark_affinity": 0.200,
        "light_affinity": 0.001,
        "life_affinity": 0.001,
        "death_affinity": 0.0001
    },
    "Лучник": {
        "health": 100,
        "mana": 87.5,
        "strength": 10,
        "speed": 14,
        "agility": 15,
        "control": 7,
        "fire_affinity": 0.100,
        "water_affinity": 0.001,
        "air_affinity": 0.200,
        "earth_affinity": 0.001,
        "dark_affinity": 0.001,
        "light_affinity": 0.001,
        "life_affinity": 0.001,
        "death_affinity": 0.00001
    },
    "Укротитель": {
        "health": 95,
        "mana": 250,
        "strength": 10,
        "speed": 13,
        "agility": 12,
        "control": 20,
        "fire_affinity": 0.001,
        "water_affinity": 0.001,
        "air_affinity": 0.001,
        "earth_affinity": 0.150,
        "dark_affinity": 0.001,
        "light_affinity": 0.001,
        "life_affinity": 0.300,
        "death_affinity": 0.00001
    }
}

# Модификаторы рас
RACE_MODIFIERS = {
    "Человек": {
        "health": 0,
        "mana": 0,
        "strength": 0,
        "speed": 2,
        "agility": 2,
        "control": -2,
        "description": "Универсальность и адаптивность. +10% к получению опыта."
    },
    "Эльф": {
        "health": -20,
        "mana": 125,
        "strength": -2,
        "speed": 1,
        "agility": 3,
        "control": 10,
        "fire_affinity_bonus": 0.100,
        "water_affinity_bonus": 0.100,
        "air_affinity_bonus": 0.100,
        "earth_affinity_bonus": 0.100,
        "life_affinity_bonus": 0.100,
        "description": "Превосходный магический контроль, хрупкое телосложение."
    },
    "Дварф": {
        "health": 25,
        "mana": 0,
        "strength": 4,
        "speed": -3,
        "agility": -3,
        "control": 1,
        "description": "Высокая физическая сила и выносливость, медленные."
    },
    "Орк": {
        "health": 30,
        "mana": -75,
        "strength": 6,
        "speed": 1,
        "agility": -2,
        "control": -6,
        "description": "Огромная физическая сила, слабая магия."
    }
}

# Подрасы зверолюдей
BEASTFOLK_SUBRACES = {
    "Заяц": {
        "health": -10,
        "mana": 0,
        "strength": -1,
        "speed": 6,
        "agility": 4,
        "control": -1,
        "description": "Невероятная скорость и прыжки, слабая сила."
    },
    "Волк": {
        "health": 20,
        "mana": -25,
        "strength": 2,
        "speed": 3,
        "agility": 2,
        "control": -2,
        "description": "Стайный инстинкт, ночное зрение, острые клыки."
    },
    "Медведь": {
        "health": 50,
        "mana": -62,
        "strength": 5,
        "speed": -2,
        "agility": -3,
        "control": -5,
        "description": "Огромная сила и выносливость, очень медленный."
    },
    "Лиса": {
        "health": -5,
        "mana": 62,
        "strength": -1,
        "speed": 4,
        "agility": 5,
        "control": 5,
        "dark_affinity_bonus": 0.200,
        "light_affinity_bonus": 0.200,
        "description": "Хитрость, иллюзии, отличная ловкость."
    },
    "Олень": {
        "health": 10,
        "mana": 87,
        "strength": 1,
        "speed": 4,
        "agility": 3,
        "control": 7,
        "life_affinity_bonus": 0.300,
        "earth_affinity_bonus": 0.100,
        "description": "Связь с природой, магия исцеления."
    },
    "Змея": {
        "health": -15,
        "mana": 50,
        "strength": -2,
        "speed": 2,
        "agility": 6,
        "control": 4,
        "description": "Ядовитые клыки, гибкость, иммунитет к ядам."
    },
    "Свинья": {
        "health": 30,
        "mana": -37,
        "strength": 3,
        "speed": 0,
        "agility": -2,
        "control": -3,
        "description": "Хорошая сила и выносливость, атака таран."
    },
    "Бык": {
        "health": 40,
        "mana": -50,
        "strength": 4,
        "speed": 1,
        "agility": -1,
        "control": -4,
        "description": "Очень высокая физическая сила, мощный разбег."
    },
    "Кот": {
        "health": -5,
        "mana": 25,
        "strength": -1,
        "speed": 3,
        "agility": 7,
        "control": 2,
        "description": "Невероятная ловкость, приземление на лапы, ночное зрение."
    },
    "Собака": {
        "health": 15,
        "mana": -12,
        "strength": 2,
        "speed": 3,
        "agility": 3,
        "control": -1,
        "description": "Сбалансированные характеристики, верность, острое обоняние."
    },
    "Ящерица": {
        "health": 5,
        "mana": 37,
        "strength": 0,
        "speed": 1,
        "agility": 4,
        "control": 3,
        "description": "Невероятная регенерация, может отращивать конечности."
    }
}

def apply_race_modifiers(base_stats, race, subrace=None):
    """Применяет расовые модификаторы к базовым характеристикам"""
    modified_stats = base_stats.copy()
    
    # Применяем основные расовые модификаторы
    if race in RACE_MODIFIERS:
        race_mods = RACE_MODIFIERS[race]
        for stat, value in race_mods.items():
            if stat == "description":
                continue
            if stat.endswith("_affinity_bonus"):
                # Бонусы к родству со стихиями
                affinity_name = stat.replace("_bonus", "")
                if affinity_name in modified_stats:
                    modified_stats[affinity_name] += value
            elif stat in modified_stats:
                modified_stats[stat] += value
    
    # Применяем модификаторы подрасы (для зверолюдей)
    if subrace and subrace in BEASTFOLK_SUBRACES:
        subrace_mods = BEASTFOLK_SUBRACES[subrace]
        for stat, value in subrace_mods.items():
            if stat == "description":
                continue
            if stat.endswith("_affinity_bonus"):
                affinity_name = stat.replace("_bonus", "")
                if affinity_name in modified_stats:
                    modified_stats[affinity_name] += value
            elif stat in modified_stats:
                modified_stats[stat] += value
    
    # Округляем значения
    for key in modified_stats:
        if key not in ["fire_affinity", "water_affinity", "air_affinity", "earth_affinity",
                       "dark_affinity", "light_affinity", "life_affinity", "death_affinity"]:
            modified_stats[key] = int(modified_stats[key])
    
    return modified_stats

def get_stats_explanation():
    """Возвращает объяснение характеристик"""
    return """
📊 <b>ОБЪЯСНЕНИЕ ХАРАКТЕРИСТИК</b>

<b>💪 СИЛА (Strength):</b>
• Физический урон = Сила × 1.5
• HP = Сила × 10
• Грузоподъёмность = Сила × 10 кг
• Регенерация HP = Сила × 1/мин

<b>⚡ СКОРОСТЬ (Speed):</b>
• Скорость бега = Скорость × 0.5 м/с
• Время реакции = 1 / Скорость сек
• Атак в секунду = Скорость / 10

<b>🏃 ЛОВКОСТЬ (Agility):</b>
• Шанс уклонения = Ловкость × 1%
• Точность = 50% + (Ловкость × 1.5%)
• Время боя = Ловкость × 1 минута

<b>🎯 КОНТРОЛЬ (Control):</b>
• MP = Контроль × 12.5
• Магический урон = × (Контроль / 10)
• Дальность магии = Контроль × 1 метр
• Регенерация MP = Контроль × 1.25/мин

<b>🔥 РОДСТВО СО СТИХИЯМИ:</b>
• 0.001%-0.099%: Зачаточное (нет заклинаний)
• 0.100%-0.499%: Базовое (заклинания 1 ранга)
• 0.500%-0.999%: Уверенное (заклинания 1-2 ранга)
• 1.000%-4.999%: Продвинутое (заклинания 1-4 ранга)
• 5.000%+: Мастерское (заклинания 5+ ранга)

<b>📈 ПРОКАЧКА:</b>
• До 15 уровня: +2 к характеристике
• После 15 уровня: +1 к характеристике
• Каждое очко даёт +1% родства со стихиями
"""

# Состояния для ConversationHandler
CREATING_NAME, CREATING_AGE, CREATING_BACKSTORY, CREATING_APPEARANCE = range(4)
WRITING_POST_CODE, WRITING_POST_CONTENT = range(4, 6)
WRITING_SYSTEM_POST, WRITING_ASSISTANT_POST = range(6, 8)
EDITING_PARAM, REJECTING_CHAR, ADDING_ADMIN, GIVING_ITEM = range(8, 12)
ADDING_ITEM, EDITING_ITEM, DELETING_ITEM = range(12, 15)
ADDING_SKILL, EDITING_SKILL, DELETING_SKILL = range(15, 18)


# База данных
def init_db():
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица персонажей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            age_height TEXT,
            race TEXT,
            class TEXT,
            backstory TEXT,
            appearance TEXT,
            status TEXT DEFAULT 'pending',
            decline_reason TEXT,
            unique_code TEXT,
            character_id TEXT,
            health INTEGER DEFAULT 100,
            mana INTEGER DEFAULT 100,
            strength INTEGER DEFAULT 5,
            speed INTEGER DEFAULT 5,
            agility INTEGER DEFAULT 5,
            control INTEGER DEFAULT 5,
            exp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            skill_points INTEGER DEFAULT 0,
            hc_coins INTEGER DEFAULT 0,
            fire_affinity REAL DEFAULT 0.2,
            water_affinity REAL DEFAULT 0.1,
            air_affinity REAL DEFAULT 0.4,
            earth_affinity REAL DEFAULT 0.5,
            dark_affinity REAL DEFAULT 0.002,
            light_affinity REAL DEFAULT 0.004,
            life_affinity REAL DEFAULT 0.004,
            death_affinity REAL DEFAULT 0.00002,
            achievements TEXT DEFAULT 'Обладатель системы',
            group_name TEXT DEFAULT '-',
            character_photo_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица администраторов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT DEFAULT 'admin',
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица постов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT,
            content TEXT,
            post_type TEXT DEFAULT 'character',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            message_id INTEGER
        )
    ''')
    
    # Таблица настроек чатов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_type TEXT UNIQUE,
            chat_id INTEGER,
            thread_id INTEGER,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица предметов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT,
            item_name TEXT,
            item_type TEXT,
            quantity INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Таблица навыков
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id TEXT,
            skill_name TEXT,
            skill_type TEXT,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    
    # Проверяем и добавляем колонки если их нет
    cursor.execute("PRAGMA table_info(characters)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'character_photo_id' not in columns:
        cursor.execute('ALTER TABLE characters ADD COLUMN character_photo_id TEXT')
    
    cursor.execute("PRAGMA table_info(admins)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'role' not in columns:
        cursor.execute('ALTER TABLE admins ADD COLUMN role TEXT DEFAULT "admin"')
        cursor.execute('ALTER TABLE admins ADD COLUMN username TEXT')
    
    cursor.execute("PRAGMA table_info(posts)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'post_type' not in columns:
        cursor.execute('ALTER TABLE posts ADD COLUMN post_type TEXT DEFAULT "character"')
    
    # Добавляем главного администратора
    cursor.execute('INSERT OR IGNORE INTO admins (user_id, username, role) VALUES (?, ?, ?)', 
                  (SUPER_ADMIN_ID, "главный_админ", "super_admin"))
    
    conn.commit()
    conn.close()

# ========== УТИЛИТНЫЕ ФУНКЦИИ ==========

def check_level_up(character_id):
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT exp, level FROM characters WHERE character_id = ?', (character_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return False
    
    exp, current_level = result
    
    if current_level < 25 and exp >= LEVEL_SYSTEM[current_level]:
        new_level = current_level + 1
        cursor.execute('UPDATE characters SET level = ?, exp = exp - ? WHERE character_id = ?', 
                      (new_level, LEVEL_SYSTEM[current_level], character_id))
        conn.commit()
        conn.close()
        return new_level
    
    conn.close()
    return False

def get_level_progress(exp, level):
    if level >= 25:
        return "Макс. уровень"
    current_level_exp = LEVEL_SYSTEM[level]
    return f"{exp}/{current_level_exp}"

def get_chat_setting(setting_type):
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id, thread_id FROM chat_settings WHERE setting_type = ?', (setting_type,))
    result = cursor.fetchone()
    conn.close()
    return result

def set_chat_setting(setting_type, chat_id, thread_id=None):
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO chat_settings (setting_type, chat_id, thread_id)
        VALUES (?, ?, ?)
    ''', (setting_type, chat_id, thread_id))
    conn.commit()
    conn.close()

def is_admin(user_id):
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_admin_role(user_id):
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT role FROM admins WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def is_super_admin(user_id):
    return user_id == SUPER_ADMIN_ID

def add_admin(user_id, username, role='admin'):
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO admins (user_id, username, role)
        VALUES (?, ?, ?)
    ''', (user_id, username, role))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM admins WHERE user_id = ? AND user_id != ?', (user_id, SUPER_ADMIN_ID))
    conn.commit()
    conn.close()

def get_admins():
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, role FROM admins')
    admins = cursor.fetchall()
    conn.close()
    return admins

def register_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()

async def send_status_notification(context: ContextTypes.DEFAULT_TYPE, message: str):
    try:
        setting = get_chat_setting('status')
        if setting:
            chat_id, thread_id = setting
            await context.bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=message,
                parse_mode='HTML'
            )
        else:
            logger.warning("Не настроен чат для статусов")
    except Exception as e:
        logger.error(f"Ошибка отправки в тему статусов: {e}")

async def send_character_notification(context: ContextTypes.DEFAULT_TYPE, message: str, photo_id=None):
    try:
        setting = get_chat_setting('characters')
        if setting:
            chat_id, thread_id = setting
            
            if photo_id:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    photo=photo_id,
                    caption=message,
                    parse_mode='HTML'
                )
            else:
                if len(message) > 1024:
                    parts = [message[i:i+1024] for i in range(0, len(message), 1024)]
                    for part in parts:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            message_thread_id=thread_id,
                            text=part,
                            parse_mode='HTML'
                        )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        message_thread_id=thread_id,
                        text=message,
                        parse_mode='HTML'
                    )
        else:
            logger.warning("Не настроен чат для персонажей")
    except Exception as e:
        logger.error(f"Ошибка отправки в тему персонажей: {e}")

async def send_post_to_topic(context: ContextTypes.DEFAULT_TYPE, character_name: str, post_content: str, post_type='character'):
    try:
        setting = get_chat_setting('posts')
        if setting:
            chat_id, thread_id = setting
            
            if post_type == 'system':
                message_text = f"<b>⚙️ СИСТЕМА</b>\n\n{post_content}"
            elif post_type == 'assistant':
                message_text = f"<b>👨‍💼 ПОМОЩНИК СИСТЕМЫ</b>\n\n{post_content}"
            elif ' & ' in character_name:
                names = character_name.split(' & ')
                centered_names = '\n'.join([f"<b>{name}</b>" for name in names])
                message_text = f"{centered_names}\n\n{post_content}"
            else:
                message_text = f"<b>{character_name}</b>\n\n{post_content}"
            
            message = await context.bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=message_text,
                parse_mode='HTML'
            )
            return message.message_id
        else:
            logger.warning("Не настроен чат для постов")
            return None
    except Exception as e:
        logger.error(f"Ошибка отправки в тему постов: {e}")
        return None

def format_uptime(uptime):
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_text = []
    if days > 0:
        uptime_text.append(f"{days} д.")
    if hours > 0:
        uptime_text.append(f"{hours} ч.")
    if minutes > 0:
        uptime_text.append(f"{minutes} мин.")
    if seconds > 0 and (days == 0 and hours == 0):
        uptime_text.append(f"{seconds} сек.")
    
    return " ".join(uptime_text) if uptime_text else "0 сек."

# ========== УПРАВЛЕНИЕ ПРЕДМЕТАМИ ==========

async def admin_items_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить предмет", callback_data="admin_add_item")],
        [InlineKeyboardButton("✏️ Редактировать предмет", callback_data="admin_edit_item")],
        [InlineKeyboardButton("🗑️ Удалить предмет", callback_data="admin_delete_item")],
        [InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📦 Управление предметами:\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def admin_add_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return ConversationHandler.END
    
    # Получаем список персонажей
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.character_id, c.name, u.username
        FROM characters c
        LEFT JOIN users u ON c.user_id = u.user_id
        WHERE c.status = 'approved'
        ORDER BY c.name
        LIMIT 20
    ''')
    characters = cursor.fetchall()
    conn.close()
    
    if not characters:
        await query.edit_message_text("❌ Нет одобренных персонажей.")
        return ConversationHandler.END
    
    context.user_data['item_action'] = 'add'
    context.user_data['available_characters'] = characters
    
    keyboard = []
    for char_id, name, username in characters:
        button_text = f"{name} (@{username})"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"itemchar_{char_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_items_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "➕ Добавление предмета\n\n"
        "Выберите персонажа:",
        reply_markup=reply_markup
    )

async def item_select_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    char_id = query.data.replace("itemchar_", "")
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM characters WHERE character_id = ?', (char_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        await query.edit_message_text("❌ Персонаж не найден.")
        return ConversationHandler.END
    
    char_name = result[0]
    context.user_data['item_character_id'] = char_id
    context.user_data['item_character_name'] = char_name
    
    await query.edit_message_text(
        f"➕ Добавление предмета для: {char_name}\n\n"
        "Введите данные в формате:\n"
        "<название> | <тип> | <количество>\n\n"
        "Пример: Меч огня | Оружие | 1\n\n"
        "Типы: Оружие, Броня, Зелье, Материал, Прочее\n"
        "Для отмены введите /cancel"
    )
    
    return ADDING_ITEM

async def add_item_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == '/cancel':
        await update.message.reply_text("❌ Добавление предмета отменено.")
        return ConversationHandler.END
    
    parts = text.split('|')
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ Неверный формат!\n\n"
            "Используйте: <название> | <тип> | <количество>\n"
            "Пример: Меч огня | Оружие | 1"
        )
        return ADDING_ITEM
    
    item_name = parts[0].strip()
    item_type = parts[1].strip()
    quantity_str = parts[2].strip()
    
    try:
        quantity = int(quantity_str)
        if quantity <= 0:
            raise ValueError("Количество должно быть положительным")
    except ValueError as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        return ADDING_ITEM
    
    character_id = context.user_data.get('item_character_id')
    char_name = context.user_data.get('item_character_name')
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже такой предмет
    cursor.execute('''
        SELECT id, quantity FROM items 
        WHERE character_id = ? AND item_name = ? AND item_type = ?
    ''', (character_id, item_name, item_type))
    existing_item = cursor.fetchone()
    
    if existing_item:
        # Увеличиваем количество
        item_id, old_quantity = existing_item
        new_quantity = old_quantity + quantity
        cursor.execute('UPDATE items SET quantity = ? WHERE id = ?', (new_quantity, item_id))
        action_text = f"увеличено количество с {old_quantity} до {new_quantity}"
    else:
        # Добавляем новый предмет
        cursor.execute('''
            INSERT INTO items (character_id, item_name, item_type, quantity)
            VALUES (?, ?, ?, ?)
        ''', (character_id, item_name, item_type, quantity))
        action_text = f"добавлен новый предмет (x{quantity})"
    
    # Получаем user_id для уведомления
    cursor.execute('SELECT user_id FROM characters WHERE character_id = ?', (character_id,))
    target_user_id = cursor.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    try:
        await context.bot.send_message(
            target_user_id,
            f"📦 Вам выдан предмет!\n\n"
            f"🎁 Предмет: {item_name}\n"
            f"📋 Тип: {item_type}\n"
            f"📊 Количество: {quantity}\n"
            f"👤 Персонаж: {char_name}"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")
    
    await update.message.reply_text(
        f"✅ Предмет '{item_name}' ({item_type}) {action_text} для персонажа {char_name}"
    )
    
    # Очищаем данные
    context.user_data.pop('item_character_id', None)
    context.user_data.pop('item_character_name', None)
    context.user_data.pop('item_action', None)
    
    return ConversationHandler.END

# ========== УПРАВЛЕНИЕ НАВЫКАМИ ==========

async def admin_skills_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить навык", callback_data="admin_add_skill")],
        [InlineKeyboardButton("✏️ Редактировать навык", callback_data="admin_edit_skill")],
        [InlineKeyboardButton("🗑️ Удалить навык", callback_data="admin_delete_skill")],
        [InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚔️ Управление навыками:\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def admin_add_skill_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return ConversationHandler.END
    
    # Получаем список персонажей
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.character_id, c.name, u.username
        FROM characters c
        LEFT JOIN users u ON c.user_id = u.user_id
        WHERE c.status = 'approved'
        ORDER BY c.name
        LIMIT 20
    ''')
    characters = cursor.fetchall()
    conn.close()
    
    if not characters:
        await query.edit_message_text("❌ Нет одобренных персонажей.")
        return ConversationHandler.END
    
    context.user_data['skill_action'] = 'add'
    
    keyboard = []
    for char_id, name, username in characters:
        button_text = f"{name} (@{username})"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"skillchar_{char_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_skills_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "➕ Добавление навыка\n\n"
        "Выберите персонажа:",
        reply_markup=reply_markup
    )

async def skill_select_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    char_id = query.data.replace("skillchar_", "")
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM characters WHERE character_id = ?', (char_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        await query.edit_message_text("❌ Персонаж не найден.")
        return ConversationHandler.END
    
    char_name = result[0]
    context.user_data['skill_character_id'] = char_id
    context.user_data['skill_character_name'] = char_name
    
    await query.edit_message_text(
        f"➕ Добавление навыка для: {char_name}\n\n"
        "Введите данные в формате:\n"
        "<название> | <тип> | <описание>\n\n"
        "Пример: Огненный шар | Активный | Мощное заклинание огня\n\n"
        "Типы: Активный, Пассивный\n"
        "Для отмены введите /cancel"
    )
    
    return ADDING_SKILL

async def add_skill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == '/cancel':
        await update.message.reply_text("❌ Добавление навыка отменено.")
        return ConversationHandler.END
    
    parts = text.split('|')
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ Неверный формат!\n\n"
            "Используйте: <название> | <тип> | <описание>\n"
            "Пример: Огненный шар | Активный | Мощное заклинание огня"
        )
        return ADDING_SKILL
    
    skill_name = parts[0].strip()
    skill_type = parts[1].strip()
    description = parts[2].strip()
    
    if skill_type not in ['Активный', 'Пассивный']:
        await update.message.reply_text("❌ Тип должен быть 'Активный' или 'Пассивный'")
        return ADDING_SKILL
    
    character_id = context.user_data.get('skill_character_id')
    char_name = context.user_data.get('skill_character_name')
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO skills (character_id, skill_name, skill_type, description)
        VALUES (?, ?, ?, ?)
    ''', (character_id, skill_name, skill_type, description))
    
    # Получаем user_id для уведомления
    cursor.execute('SELECT user_id FROM characters WHERE character_id = ?', (character_id,))
    target_user_id = cursor.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    try:
        await context.bot.send_message(
            target_user_id,
            f"⚔️ Вы получили новый навык!\n\n"
            f"🎯 Навык: {skill_name}\n"
            f"📋 Тип: {skill_type}\n"
            f"📝 Описание: {description}\n"​​​​​​​​​​​​​​​​
            f"👤 Персонаж: {char_name}"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")
    
    await update.message.reply_text(
        f"✅ Навык '{skill_name}' ({skill_type}) добавлен персонажу {char_name}"
    )
    
    # Очищаем данные
    context.user_data.pop('skill_character_id', None)
    context.user_data.pop('skill_character_name', None)
    context.user_data.pop('skill_action', None)
    
    return ConversationHandler.END

async def admin_edit_skill_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return ConversationHandler.END
    
    # Получаем список персонажей с навыками
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT c.character_id, c.name, u.username
        FROM characters c
        LEFT JOIN users u ON c.user_id = u.user_id
        INNER JOIN skills s ON c.character_id = s.character_id
        WHERE c.status = 'approved'
        ORDER BY c.name
    ''')
    characters = cursor.fetchall()
    conn.close()
    
    if not characters:
        await query.edit_message_text("❌ Нет персонажей с навыками.")
        return ConversationHandler.END
    
    context.user_data['skill_action'] = 'edit'
    
    keyboard = []
    for char_id, name, username in characters:
        button_text = f"{name} (@{username})"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"editskillchar_{char_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_skills_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✏️ Редактирование навыка\n\n"
        "Выберите персонажа:",
        reply_markup=reply_markup
    )

async def edit_skill_select_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    char_id = query.data.replace("editskillchar_", "")
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM characters WHERE character_id = ?', (char_id,))
    char_result = cursor.fetchone()
    
    if not char_result:
        await query.edit_message_text("❌ Персонаж не найден.")
        return ConversationHandler.END
    
    char_name = char_result[0]
    
    cursor.execute('''
        SELECT id, skill_name, skill_type, description
        FROM skills
        WHERE character_id = ?
        ORDER BY skill_name
    ''', (char_id,))
    skills = cursor.fetchall()
    conn.close()
    
    if not skills:
        await query.edit_message_text("❌ У этого персонажа нет навыков.")
        return ConversationHandler.END
    
    context.user_data['skill_character_id'] = char_id
    context.user_data['skill_character_name'] = char_name
    
    keyboard = []
    for skill_id, skill_name, skill_type, description in skills:
        button_text = f"{skill_name} ({skill_type})"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"editskill_{skill_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_edit_skill")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✏️ Навыки персонажа: {char_name}\n\n"
        "Выберите навык для редактирования:",
        reply_markup=reply_markup
    )

async def edit_skill_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    skill_id = int(query.data.replace("editskill_", ""))
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT skill_name, skill_type, description FROM skills WHERE id = ?', (skill_id,))
    skill = cursor.fetchone()
    conn.close()
    
    if not skill:
        await query.edit_message_text("❌ Навык не найден.")
        return ConversationHandler.END
    
    skill_name, skill_type, description = skill
    context.user_data['editing_skill_id'] = skill_id
    context.user_data['editing_skill_name'] = skill_name
    
    await query.edit_message_text(
        f"✏️ Редактирование навыка: {skill_name}\n\n"
        f"📋 Текущий тип: {skill_type}\n"
        f"📝 Текущее описание: {description}\n\n"
        "Введите новые данные в формате:\n"
        "<название> | <тип> | <описание>\n\n"
        "Пример: Огненный шар | Активный | Мощное заклинание огня\n\n"
        "Для отмены введите /cancel"
    )
    
    return EDITING_SKILL

async def edit_skill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == '/cancel':
        await update.message.reply_text("❌ Редактирование навыка отменено.")
        return ConversationHandler.END
    
    parts = text.split('|')
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ Неверный формат!\n\n"
            "Используйте: <название> | <тип> | <описание>\n"
            "Пример: Огненный шар | Активный | Мощное заклинание огня"
        )
        return EDITING_SKILL
    
    skill_name = parts[0].strip()
    skill_type = parts[1].strip()
    description = parts[2].strip()
    
    if skill_type not in ['Активный', 'Пассивный']:
        await update.message.reply_text("❌ Тип должен быть 'Активный' или 'Пассивный'")
        return EDITING_SKILL
    
    skill_id = context.user_data.get('editing_skill_id')
    char_name = context.user_data.get('skill_character_name')
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE skills 
        SET skill_name = ?, skill_type = ?, description = ?
        WHERE id = ?
    ''', (skill_name, skill_type, description, skill_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ Навык обновлён!\n\n"
        f"🎯 Новое название: {skill_name}\n"
        f"📋 Новый тип: {skill_type}\n"
        f"📝 Новое описание: {description}\n"
        f"👤 Персонаж: {char_name}"
    )
    
    # Очищаем данные
    context.user_data.pop('editing_skill_id', None)
    context.user_data.pop('editing_skill_name', None)
    context.user_data.pop('skill_character_id', None)
    context.user_data.pop('skill_character_name', None)
    
    return ConversationHandler.END

async def admin_delete_skill_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return ConversationHandler.END
    
    # Получаем список персонажей с навыками
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT c.character_id, c.name, u.username
        FROM characters c
        LEFT JOIN users u ON c.user_id = u.user_id
        INNER JOIN skills s ON c.character_id = s.character_id
        WHERE c.status = 'approved'
        ORDER BY c.name
    ''')
    characters = cursor.fetchall()
    conn.close()
    
    if not characters:
        await query.edit_message_text("❌ Нет персонажей с навыками.")
        return ConversationHandler.END
    
    context.user_data['skill_action'] = 'delete'
    
    keyboard = []
    for char_id, name, username in characters:
        button_text = f"{name} (@{username})"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"delskillchar_{char_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_skills_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🗑️ Удаление навыка\n\n"
        "Выберите персонажа:",
        reply_markup=reply_markup
    )

async def delete_skill_select_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    char_id = query.data.replace("delskillchar_", "")
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM characters WHERE character_id = ?', (char_id,))
    char_result = cursor.fetchone()
    
    if not char_result:
        await query.edit_message_text("❌ Персонаж не найден.")
        return ConversationHandler.END
    
    char_name = char_result[0]
    
    cursor.execute('''
        SELECT id, skill_name, skill_type, description
        FROM skills
        WHERE character_id = ?
        ORDER BY skill_name
    ''', (char_id,))
    skills = cursor.fetchall()
    conn.close()
    
    if not skills:
        await query.edit_message_text("❌ У этого персонажа нет навыков.")
        return ConversationHandler.END
    
    context.user_data['skill_character_id'] = char_id
    context.user_data['skill_character_name'] = char_name
    
    keyboard = []
    for skill_id, skill_name, skill_type, description in skills:
        button_text = f"{skill_name} ({skill_type})"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"delskill_{skill_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_delete_skill")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🗑️ Навыки персонажа: {char_name}\n\n"
        "Выберите навык для удаления:",
        reply_markup=reply_markup
    )

async def delete_skill_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    skill_id = int(query.data.replace("delskill_", ""))
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT skill_name, skill_type, description FROM skills WHERE id = ?', (skill_id,))
    skill = cursor.fetchone()
    conn.close()
    
    if not skill:
        await query.edit_message_text("❌ Навык не найден.")
        return ConversationHandler.END
    
    skill_name, skill_type, description = skill
    char_name = context.user_data.get('skill_character_name')
    
    context.user_data['deleting_skill_id'] = skill_id
    context.user_data['deleting_skill_name'] = skill_name
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirmdelskill_{skill_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data="admin_delete_skill")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ Вы уверены, что хотите удалить навык?\n\n"
        f"🎯 Навык: {skill_name}\n"
        f"📋 Тип: {skill_type}\n"
        f"📝 Описание: {description}\n"
        f"👤 Персонаж: {char_name}\n\n"
        "Это действие нельзя отменить!",
        reply_markup=reply_markup
    )

async def delete_skill_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    skill_id = context.user_data.get('deleting_skill_id')
    skill_name = context.user_data.get('deleting_skill_name')
    char_name = context.user_data.get('skill_character_name')
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM skills WHERE id = ?', (skill_id,))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(
        f"✅ Навык '{skill_name}' удалён у персонажа {char_name}!"
    )
    
    # Очищаем данные
    context.user_data.pop('deleting_skill_id', None)
    context.user_data.pop('deleting_skill_name', None)
    context.user_data.pop('skill_character_id', None)
    context.user_data.pop('skill_character_name', None)
    
    return ConversationHandler.END



# ========== КОМАНДЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_id = update.message.from_user.id
        username = update.message.from_user.username
        first_name = update.message.from_user.first_name
        last_name = update.message.from_user.last_name
        
        register_user(user_id, username, first_name, last_name)
        
        keyboard = [
            [InlineKeyboardButton("🎭 Создать персонажа", callback_data="create_character")],
            [InlineKeyboardButton("📊 Мои персонажи", callback_data="my_characters")],
            [InlineKeyboardButton("📈 Статистика", callback_data="show_stats")],
            [InlineKeyboardButton("📝 Написать пост", callback_data="start_post_menu")],
            [InlineKeyboardButton("⚡ Прокачка", callback_data="upgrade_menu")],
            [InlineKeyboardButton("📖 Справка по характеристикам", callback_data="stats_guide")]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎮 Добро пожаловать в NoNameGame, {first_name}!\n\n"
            "Выберите действие из меню ниже:",
            reply_markup=reply_markup
        )
    else:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🎭 Создать персонажа", callback_data="create_character")],
            [InlineKeyboardButton("📊 Мои персонажи", callback_data="my_characters")],
            [InlineKeyboardButton("📈 Статистика", callback_data="show_stats")],
            [InlineKeyboardButton("📝 Написать пост", callback_data="start_post_menu")],
            [InlineKeyboardButton("⚡ Прокачка", callback_data="upgrade_menu")],
            [InlineKeyboardButton("📖 Справка по характеристикам", callback_data="stats_guide")]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎮 Добро пожаловать в NoNameGame!\n\n"
            "Выберите действие из меню ниже:",
            reply_markup=reply_markup
        )
    
    return ConversationHandler.END

async def help_nng(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🎮 <b>ПОЛНЫЙ ГАЙД ПО NO NAMEGAME</b> 🎮

📋 <b>ОСНОВНЫЕ КОМАНДЫ:</b>
/start - Главное меню бота

🎭 <b>СОЗДАНИЕ ПЕРСОНАЖА:</b>
1. Нажмите "🎭 Создать персонажа"
2. Введите имя персонажа (до 50 символов)
3. Введите возраст и рост (например: 25 лет, 180 см)
4. Выберите расу из предложенных вариантов
5. Выберите класс из предложенных вариантов
6. Напишите предысторию персонажа (до 800 символов)
7. Отправьте фотографию персонажа ИЛИ описание внешности

⏳ После отправки анкета отправляется на проверку администраторам.
Ожидайте одобрения. Вы получите уведомление когда вашего персонажа проверят.

📊 <b>МОИ ПЕРСОНАЖИ:</b>
• Нажмите "📊 Мои персонажи" для просмотра всех ваших персонажей
• Вы увидите их статусы (одобрен, отклонен, на проверке)
• Для одобренных персонажей будет указан ID

📝 <b>НАПИСАНИЕ ПОСТОВ:</b>
1. Нажмите "📝 Написать пост"
2. Выберите персонажа (или оба для совместного поста)
3. Введите уникальный код персонажа (если требуется)
4. Присылайте текст поста сообщениями
5. Когда закончите, отправьте /end_post
6. Для отмены используйте /cancel_post

⏰ <b>ВРЕМЕННОЙ ЛИМИТ:</b>
• Между постами должен быть перерыв 10 минут
• Для совместных постов указывайте, какой персонаж говорит/действует

⚡ <b>ПРОКАЧКА ХАРАКТЕРИСТИК:</b>
1. Нажмите "⚡ Прокачка"
2. Если есть очки характеристики, выберите характеристику для улучшения
3. Каждое очко дает +2 к характеристике (до 15 уровня) или +1 (после 15)
4. При прокачке также увеличивается родство со стихиями

📈 <b>СТАТИСТИКА ПЕРСОНАЖА:</b>
• Нажмите "📈 Статистика" для просмотра всех характеристик
• Увидите уровень, опыт, здоровье, ману, силу, скорость и другие параметры
• Также отображаются родство со стихиями и инвентарь

💡 <b>ВАЖНЫЕ ПРАВИЛА:</b>
1. Максимум 2 персонажа на игрока
2. Уникальный код персонажа - это ваш пароль, храните его в безопасности
3. Посты должны соответствовать сеттингу игры
4. Уважайте других игроков и администрацию
5. За нарушение правил возможны санкции

🔧 <b>ПОМОЩЬ:</b>
• Для технических проблем обращайтесь к администрации
• Следите за обновлениями в официальных чатах
• Не передавайте свой уникальный код другим лицам

🎉 <b>УДАЧНОЙ ИГРЫ!</b>
Если возникнут вопросы - не стесняйтесь задавать их в чате игры.
"""
    
    await update.message.reply_text(help_text, parse_mode='HTML')

async def bot_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if BOT_START_TIME is None:
        await update.message.reply_text("🤖 Бот только что запущен!")
        return
    
    current_time = datetime.now()
    uptime = current_time - BOT_START_TIME
    
    message = await update.message.reply_text(
        f"⏳ <b>Загружаем информацию о времени работы...</b>",
        parse_mode='HTML'
    )
    
    chat_id = message.chat_id
    message_id = message.message_id
    
    asyncio.create_task(update_uptime_message(context, chat_id, message_id))
    uptime_messages[f"{chat_id}_{message_id}"] = True

async def update_uptime_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    key = f"{chat_id}_{message_id}"
    
    try:
        while key in uptime_messages and uptime_messages[key]:
            current_time = datetime.now()
            uptime = current_time - BOT_START_TIME
            
            uptime_str = format_uptime(uptime)
            
            total_seconds = uptime.total_seconds()
            days = uptime.days
            hours = int((total_seconds // 3600) % 24)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            
            progress = int((minutes / 60) * 10)
            progress_bar = "█" * progress + "░" * (10 - progress)
            
            conn = sqlite3.connect('nonamegame.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM users')
            users_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM characters WHERE status = "approved"')
            characters_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM posts')
            posts_count = cursor.fetchone()[0]
            
            conn.close()
            
            message_text = f"""
⏰ <b>ВРЕМЯ РАБОТЫ БОТА</b> ⏰

🕐 <b>Работает:</b> {uptime_str}
📅 <b>Запущен:</b> {BOT_START_TIME.strftime('%d.%m.%Y %H:%M:%S')}
🕒 <b>Текущее время:</b> {current_time.strftime('%d.%m.%Y %H:%M:%S')}

<b>Прогресс текущего часа:</b>
[{progress_bar}] {minutes:02d}:{seconds:02d}

📊 <b>Статистика бота:</b>
• 👥 Игроков: {users_count}
• 🎭 Персонажей: {characters_count}
• 📝 Постов: {posts_count}
• ⚡ Статус: Работает стабильно

<code>Обновляется каждые 30 секунд.</code>
"""
            
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=message_text,
                    parse_mode='HTML'
                )
            except Exception as e:
                error_msg = str(e)
                if "Message to edit not found" in error_msg:
                    uptime_messages.pop(key, None)
                    logger.info(f"Сообщение {key} удалено, останавливаем мониторинг")
                    break
                elif "Flood control exceeded" in error_msg:
                    logger.warning(f"Flood control для {key}, увеличиваем интервал")
                    await asyncio.sleep(60)
                    continue
                else:
                    logger.error(f"Ошибка обновления uptime сообщения {key}: {e}")
                    await asyncio.sleep(5)
                    continue
            
            await asyncio.sleep(30)
        
        logger.info(f"Мониторинг остановлен для {key}")
            
    except asyncio.CancelledError:
        logger.info(f"Задача мониторинга отменена для {key}")
        uptime_messages.pop(key, None)
    except Exception as e:
        logger.error(f"Критическая ошибка в задаче обновления uptime для {key}: {e}", exc_info=True)
        uptime_messages.pop(key, None)

async def stop_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_chat_id = update.effective_chat.id
    
    active_keys = [key for key in uptime_messages.keys() if key.startswith(f"{user_chat_id}_")]
    
    if not active_keys:
        await update.message.reply_text("ℹ️ У вас нет активных сообщений мониторинга в этом чате.")
        return
    
    if len(active_keys) > 1 and context.args:
        try:
            index = int(context.args[0]) - 1
            if 0 <= index < len(active_keys):
                key_to_stop = active_keys[index]
                uptime_messages[key_to_stop] = False
                await update.message.reply_text(f"✅ Остановлен мониторинг #{index + 1}.")
                return
        except (ValueError, IndexError):
            pass
        
        text = "📋 <b>Активные мониторинги в этом чате:</b>\n\n"
        for i, key in enumerate(active_keys, 1):
            text += f"{i}. Мониторинг #{i} (ID: {key.split('_')[1][:8]}...)\n"
        
        text += "\nДля остановки используйте: /stop_uptime <номер>"
        await update.message.reply_text(text, parse_mode='HTML')
        return
    
    stopped_count = 0
    for key in active_keys:
        uptime_messages[key] = False
        stopped_count += 1
    
    await update.message.reply_text(f"✅ Остановлено {stopped_count} сообщений мониторинга.")

async def maintenance_notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if context.args:
        duration = " ".join(context.args)
        message = (
            f"⚠️ <b>ТЕХНИЧЕСКИЕ РАБОТЫ</b> ⚠️\n\n"
            f"Бот будет временно недоступен через несколько минут.\n"
            f"⏳ <b>Приблизительное время работ:</b> {duration}\n\n"
            f"Приносим извинения за неудобства!\n"
            f"🔧 Ведутся технические шоколадки..."
        )
    else:
        message = (
            f"⚠️ <b>ТЕХНИЧЕСКИЕ РАБОТЫ</b> ⚠️\n\n"
            f"Бот будет временно недоступен через несколько минут.\n"
            f"Приносим извинения за неудобства!\n"
            f"🔧 Ведутся технические шоколадки..."
        )
    
    await update.message.reply_text(message, parse_mode='HTML')

async def setup_posts_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    chat_id = update.effective_chat.id
    thread_id = update.effective_message.message_thread_id if update.effective_message.is_topic_message else None
    
    set_chat_setting('posts', chat_id, thread_id)
    
    if thread_id:
        await update.message.reply_text("✅ Чат для постов настроен! Теперь посты игроков будут приходить в эту тему.")
    else:
        await update.message.reply_text("✅ Чат для постов настроен! Теперь посты игроков будут приходить в этот чат.")

async def setup_characters_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    chat_id = update.effective_chat.id
    thread_id = update.effective_message.message_thread_id if update.effective_message.is_topic_message else None
    
    set_chat_setting('characters', chat_id, thread_id)
    
    if thread_id:
        await update.message.reply_text("✅ Чат для персонажей настроен! Уведомления о персонажах будут приходить в эту тему.")
    else:
        await update.message.reply_text("✅ Чат для персонажей настроен! Уведомления о персонажах будут приходить в этот чат.")

async def setup_status_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    chat_id = update.effective_chat.id
    thread_id = update.effective_message.message_thread_id if update.effective_message.is_topic_message else None
    
    set_chat_setting('status', chat_id, thread_id)
    
    if thread_id:
        await update.message.reply_text("✅ Чат для статусов настроен! Уведомления о процессе постов будут приходить в эту тему.")
    else:
        await update.message.reply_text("✅ Чат для статусов настроен! Уведомления о процессе постов будут приходить в этот чат.")

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    posts_setting = get_chat_setting('posts')
    characters_setting = get_chat_setting('characters')
    status_setting = get_chat_setting('status')
    
    text = "⚙️ Текущие настройки чатов:\n\n"
    
    if posts_setting:
        chat_id, thread_id = posts_setting
        text += f"📝 Посты: Чат {chat_id}" + (f", тема {thread_id}" if thread_id else "") + "\n"
    else:
        text += "📝 Посты: ❌ Не настроено\n"
    
    if characters_setting:
        chat_id, thread_id = characters_setting
        text += f"🎭 Персонажи: Чат {chat_id}" + (f", тема {thread_id}" if thread_id else "") + "\n"
    else:
        text += "🎭 Персонажи: ❌ Не настроено\n"
    
    if status_setting:
        chat_id, thread_id = status_setting
        text += f"📊 Статусы: Чат {chat_id}" + (f", тема {thread_id}" if thread_id else "") + "\n"
    else:
        text += "📊 Статусы: ❌ Не настроено\n"
    
    text += "\nИспользуйте команды:\n"
    text += "/set_posts_here - настроить чат для постов\n"
    text += "/set_characters_here - настроить чат для персонажей\n"
    text += "/set_status_here - настроить чат для статусов"
    
    await update.message.reply_text(text)

async def admin_give_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Использование: /give_points <ID_персонажа> <количество_очков>\n\n"
            "Пример: /give_points ABC 5"
        )
        return
    
    character_id = context.args[0]
    points = int(context.args[1])
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name, user_id FROM characters WHERE character_id = ?', (character_id,))
    character = cursor.fetchone()
    
    if not character:
        await update.message.reply_text("❌ Персонаж с таким ID не найден.")
        conn.close()
        return
    
    char_name, target_user_id = character
    
    cursor.execute('UPDATE characters SET skill_points = skill_points + ? WHERE character_id = ?', (points, character_id))
    conn.commit()
    conn.close()
    
    try:
        await context.bot.send_message(
            target_user_id,
            f"🎯 Вам выданы очки характеристики!\n\n"
            f"📊 Количество: {points} очков\n"
            f"👤 Персонаж: {char_name}\n\n"
            f"🆔 ID персонажа: {character_id}\n\n"
            "Используйте очки для прокачки характеристик в меню прокачки."
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")
    
    await update.message.reply_text(f"✅ {points} очков характеристики выдано персонажу {char_name} (ID: {character_id})")

async def admin_give_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Использование: /give_exp <ID_персонажа> <количество_опыта>\n\n"
            "Пример: /give_exp ABC 100"
        )
        return
    
    character_id = context.args[0]
    exp_amount = int(context.args[1])
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name, user_id, level FROM characters WHERE character_id = ?', (character_id,))
    character = cursor.fetchone()
    
    if not character:
        await update.message.reply_text("❌ Персонаж с таким ID не найден.")
        conn.close()
        return
    
    char_name, target_user_id, old_level = character
    
    cursor.execute('UPDATE characters SET exp = exp + ? WHERE character_id = ?', (exp_amount, character_id))
    conn.commit()
    
    new_level = check_level_up(character_id)
    
    conn.close()
    
    level_text = ""
    if new_level:
        level_text = f"\n🎉 Уровень повышен! Новый уровень: {new_level}"
        try:
            await context.bot.send_message(
                target_user_id,
                f"🎉 Ваш персонаж '{char_name}' повысил уровень!\n\n"
                f"📊 Новый уровень: {new_level}\n"
                f"🆔 ID персонажа: {character_id}"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление о повышении уровня пользователю {target_user_id}: {e}")
    
    try:
        await context.bot.send_message(
            target_user_id,
            f"⭐ Вам выдан опыт!\n\n"
            f"📊 Количество: {exp_amount} опыта\n"
            f"👤 Персонаж: {char_name}\n"
            f"🆔 ID персонажа: {character_id}"
            + level_text
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")
    
    await update.message.reply_text(f"✅ {exp_amount} опыта выдано персонажу {char_name} (ID: {character_id}){level_text}")

async def admin_panel_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    
    keyboard = [
        [InlineKeyboardButton("👁️ Проверить анкеты", callback_data="admin_review")],
        [InlineKeyboardButton("🗑️ Удалить персонажа", callback_data="admin_delete_char")],
        [InlineKeyboardButton("⚡ Написать от системы", callback_data="admin_system_post")],
        [InlineKeyboardButton("👨‍💼 Написать от помощника", callback_data="admin_assistant_post")]
    ]
    
    if is_super_admin(user_id):
        keyboard.append([InlineKeyboardButton("👥 Управление админами", callback_data="admin_manage_admins")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ Админ-панель (группа):",
        reply_markup=reply_markup
    )

async def auto_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    await update.message.reply_text(
        "🤖 Запускаю автоматический мониторинг времени работы бота...\n\n"
        "Мониторинг будет работать 24/7 до перезапуска бота."
    )
    
    asyncio.create_task(start_auto_uptime(context))

async def start_auto_uptime(context: ContextTypes.DEFAULT_TYPE):
    try:
        AUTO_MONITOR_CHAT_ID = SUPER_ADMIN_ID
        
        message = await context.bot.send_message(
            chat_id=AUTO_MONITOR_CHAT_ID,
            text="🤖 <b>АВТОМАТИЧЕСКИЙ МОНИТОРИНГ БОТА ЗАПУЩЕН</b>\n\n"
                 "⏳ Загружаем информацию...",
            parse_mode='HTML'
        )
        
        chat_id = message.chat_id
        message_id = message.message_id
        
        asyncio.create_task(update_uptime_message(context, chat_id, message_id))
        uptime_messages[f"{chat_id}_{message_id}"] = True
        
        logger.info(f"Авто-мониторинг запущен в чате {chat_id}")
        
    except Exception as e:
        logger.error(f"Ошибка запуска авто-мониторинга: {e}")

# ========== ОБРАБОТЧИКИ CALLBACK ==========

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    logger.info(f"Callback data received: {data} from user {user_id}")
    
    try:
        if data == "create_character":
            await create_character_start(update, context)
        elif data == "my_characters":
            await show_my_characters(update, context)
        elif data == "show_stats":
            await show_character_stats(update, context)
        elif data == "stats_guide":  # НОВЫЙ
            await show_stats_guide(update, context)
        elif data == "start_post_menu":
            await start_post_menu(update, context)
        elif data == "upgrade_menu":
            await upgrade_menu(update, context)
        elif data == "admin_panel":
            await admin_panel(update, context)
        elif data == "main_menu":
            await start(update, context)
        elif data.startswith("race_"):
            await process_race_selection(update, context)
        elif data.startswith("subrace_"):  # НОВЫЙ
            await process_subrace_selection(update, context)
        elif data.startswith("class_"):
            await process_class_selection(update, context)
        # ... остальные обработчики
        elif data == "admin_review":
            await show_pending_characters(update, context)
        elif data.startswith("approve_"):
            await approve_character(update, context)
        elif data.startswith("reject_"):
            await reject_character_start(update, context)
        elif data == "admin_delete_char":
            await delete_character_menu(update, context)
        elif data.startswith("delete_char_"):
            await confirm_delete_character(update, context)
        elif data.startswith("confirm_delete_"):
            await execute_delete_character(update, context)
        elif data.startswith("upgrade_"):
            await handle_upgrade(update, context)
        elif data == "admin_give_item":
            await admin_give_item_start(update, context)
        elif data == "admin_edit_stats":
            await admin_edit_stats_menu(update, context)
        elif data.startswith("edit_"):
            parts = data.split('_')
            if len(parts) == 2:
                await admin_edit_stat(update, context)
            elif len(parts) >= 3:
                await handle_edit_parameter(update, context)
        elif data == "admin_settings":
            await admin_settings(update, context)
        elif data == "admin_system_post":
            await admin_system_post_start(update, context)
        elif data == "admin_assistant_post":
            await admin_assistant_post_start(update, context)
        elif data == "admin_all_stats":
            await admin_all_stats(update, context)
        elif data == "admin_manage_admins":
            await admin_manage_admins(update, context)
        elif data == "add_admin_menu":
            await add_admin_start(update, context)
        elif data == "remove_admin_menu":
            await remove_admin_menu(update, context)
        elif data.startswith("remove_admin_"):
            await execute_remove_admin(update, context)
        elif data == "admin_next_stat":
            await send_next_stat(update, context)
        elif data.startswith("post_char_"):
            await start_post_for_character(update, context)
        elif data.startswith("post_both_"):
            await start_post_for_both_characters(update, context)
        elif data == "admin_back_to_panel":
            await admin_panel(update, context)
        else:
            logger.warning(f"Неизвестный callback data: {data}")
            await query.edit_message_text(f"❌ Неизвестная команда: {data}")
    except Exception as e:
        logger.error(f"Ошибка в button_handler: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Ошибка: {str(e)[:100]}")
    
    return ConversationHandler.END

# ========== СОЗДАНИЕ ПЕРСОНАЖА ==========

async def create_character_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    logger.info(f"Начало создания персонажа для пользователя {user_id}")
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM characters WHERE user_id = ? AND status != "declined"', (user_id,))
    character_count = cursor.fetchone()[0]
    conn.close()
    
    if character_count >= 2:
        await query.edit_message_text("❌ У вас уже есть максимальное количество персонажей (2).")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🎭 Создание нового персонажа!\n\n"
        "📝 Введите имя персонажа (до 50 символов):"
    )
    
    return CREATING_NAME

async def create_character_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if len(text) > 50:
        await update.message.reply_text("❌ Имя слишком длинное! Максимум 50 символов.")
        return CREATING_NAME
    
    context.user_data['char_name'] = text
    
    await update.message.reply_text("✅ Отлично! Теперь введите возраст и рост (например: 25 лет, 180 см):")
    
    return CREATING_AGE

async def create_character_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    context.user_data['char_age_height'] = text
    
    races = ["Человек", "Эльф", "Дварф", "Орк", "Зверолюди"]
    keyboard = []
    
    for race in races:
        keyboard.append([InlineKeyboardButton(race, callback_data=f"race_{race}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏹 Выберите расу:", reply_markup=reply_markup)
    
    return CREATING_BACKSTORY

async def process_race_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    race = query.data.replace("race_", "")
    context.user_data['char_race'] = race
    
    classes = ["Лучник", "Маг атакующего класса", "Маг поддержки", "Ассасин", "Танк", "Воин", "Укротитель"]
    keyboard = []
    
    for class_name in classes:
        keyboard.append([InlineKeyboardButton(class_name, callback_data=f"class_{class_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("⚔️ Выберите класс:", reply_markup=reply_markup)

async def process_class_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    class_name = query.data.replace("class_", "")
    context.user_data['char_class'] = class_name
    
    # Если раса - Зверолюди, показываем выбор подрасы
    if context.user_data.get('char_race') == "Зверолюди":
        subraces = list(BEASTFOLK_SUBRACES.keys())
        keyboard = []
        
        for subrace in subraces:
            keyboard.append([InlineKeyboardButton(subrace, callback_data=f"subrace_{subrace}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🐺 Выберите вид зверочеловека:",
            reply_markup=reply_markup
        )
        return
    
    await query.edit_message_text(
        "📖 Напишите предысторию персонажа (максимум 800 символов):\n\n"
        "Пример: Родился в маленькой деревне, с детства мечтал о приключениях..."
    )
    
    return CREATING_BACKSTORY

async def process_subrace_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    subrace = query.data.replace("subrace_", "")
    context.user_data['char_subrace'] = subrace
    
    await query.edit_message_text(
        "📖 Напишите предысторию персонажа (максимум 800 символов):\n\n"
        "Пример: Родился в маленькой деревне, с детства мечтал о приключениях..."
    )
    
    return CREATING_BACKSTORY

async def create_character_backstory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if len(text) > 800:
        await update.message.reply_text("❌ Предыстория слишком длинная! Максимум 800 символов.")
        return CREATING_BACKSTORY
    
    context.user_data['char_backstory'] = text
    
    await update.message.reply_text(
        "✅ Отлично! Теперь пришлите фотографию персонажа ИЛИ описание внешности:\n\n"
        "📎 Можно отправить фото или просто написать текстовое описание"
    )
    
    return CREATING_APPEARANCE

async def create_character_appearance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo = update.message.photo[-1]
        photo_file_id = photo.file_id
        context.user_data['char_photo_id'] = photo_file_id
        appearance_text = "[Фото приложено]"
    elif update.message.text:
        appearance_text = update.message.text
        context.user_data['char_photo_id'] = None
    else:
        await update.message.reply_text("❌ Пожалуйста, отправьте фото или текстовое описание.")
        return CREATING_APPEARANCE
    
    context.user_data['char_appearance'] = appearance_text
    
    return await finalize_character(update, context)

async def finalize_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    char_name = context.user_data.get('char_name')
    char_age_height = context.user_data.get('char_age_height')
    char_race = context.user_data.get('char_race')
    char_subrace = context.user_data.get('char_subrace')  # Для зверолюдей
    char_class = context.user_data.get('char_class')
    char_backstory = context.user_data.get('char_backstory')
    char_appearance = context.user_data.get('char_appearance')
    char_photo_id = context.user_data.get('char_photo_id')
    
    # Получаем базовые характеристики класса
    base_stats = CLASS_BASE_STATS.get(char_class, CLASS_BASE_STATS["Воин"])
    
    # Применяем расовые модификаторы
    final_stats = apply_race_modifiers(base_stats, char_race, char_subrace)
    
    # Формируем полное название расы
    full_race = char_race
    if char_subrace:
        full_race = f"{char_race} ({char_subrace})"
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO characters (
            user_id, name, age_height, race, class, backstory, appearance, 
            character_photo_id, status,
            health, mana, strength, speed, agility, control,
            fire_affinity, water_affinity, air_affinity, earth_affinity,
            dark_affinity, light_affinity, life_affinity, death_affinity
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, char_name, char_age_height, full_race, char_class, 
        char_backstory, char_appearance, char_photo_id,
        final_stats['health'], final_stats['mana'],
        final_stats['strength'], final_stats['speed'], 
        final_stats['agility'], final_stats['control'],
        final_stats['fire_affinity'], final_stats['water_affinity'],
        final_stats['air_affinity'], final_stats['earth_affinity'],
        final_stats['dark_affinity'], final_stats['light_affinity'],
        final_stats['life_affinity'], final_stats['death_affinity']
    ))
    
    char_id = cursor.lastrowid
    
    cursor.execute('SELECT username FROM users WHERE user_id = ?', (user_id,))
    user_result = cursor.fetchone()
    username = user_result[0] if user_result else f"ID: {user_id}"
    
    conn.commit()
    conn.close()
    
    # Получаем описание расовых особенностей
    race_desc = RACE_MODIFIERS.get(char_race, {}).get("description", "")
    if char_subrace:
        race_desc = BEASTFOLK_SUBRACES.get(char_subrace, {}).get("description", "")
    
    # Уведомляем админов
    text = (
        "📝 <b>НОВАЯ АНКЕТА ПЕРСОНАЖА</b>\n\n"
        f"👤 <b>Игрок:</b> @{username} (ID: {user_id})\n"
        f"📛 <b>Имя:</b> {char_name}\n"
        f"🏹 <b>Раса:</b> {full_race}\n"
        f"⚔️ <b>Класс:</b> {char_class}\n"
        f"📏 <b>Возраст/рост:</b> {char_age_height}\n\n"
        f"📊 <b>Характеристики:</b>\n"
        f"❤️ HP: {final_stats['health']} | 🔵 MP: {final_stats['mana']}\n"
        f"💪 Сила: {final_stats['strength']} | ⚡ Скорость: {final_stats['speed']}\n"
        f"🏃 Ловкость: {final_stats['agility']} | 🎯 Контроль: {final_stats['control']}\n\n"
        f"✨ <b>Расовая особенность:</b> {race_desc}\n\n"
        f"📖 <b>Предыстория:</b> {char_backstory[:200]}...\n"
        f"👀 <b>Внешность:</b> {char_appearance}\n\n"
        f"🆔 <b>ID анкеты:</b> {char_id}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{char_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{char_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if char_photo_id:
            await context.bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=char_photo_id,
                caption=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Ошибка отправки в админскую беседу: {e}")
    
    # Очищаем данные
    for key in ['char_name', 'char_age_height', 'char_race', 'char_subrace', 'char_class', 
                'char_backstory', 'char_appearance', 'char_photo_id']:
        context.user_data.pop(key, None)
    
    await update.message.reply_text(
        f"✅ Анкета персонажа отправлена на проверку!\n\n"
        f"📊 Ваши стартовые характеристики:\n"
        f"❤️ HP: {final_stats['health']} | 🔵 MP: {final_stats['mana']}\n"
        f"💪 Сила: {final_stats['strength']} | ⚡ Скорость: {final_stats['speed']}\n"
        f"🏃 Ловкость: {final_stats['agility']} | 🎯 Контроль: {final_stats['control']}\n\n"
        f"✨ Расовая особенность: {race_desc}\n\n"
        "Ожидайте одобрения администраторов."
    )
    
    return ConversationHandler.END

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Очищаем данные
    for key in ['char_name', 'char_age_height', 'char_race', 'char_class', 'char_backstory', 'char_appearance', 'char_photo_id']:
        context.user_data.pop(key, None)
    
    await update.message.reply_text("❌ Создание персонажа отменено.")
    return ConversationHandler.END

# ========== НАПИСАНИЕ ПОСТОВ ==========

async def start_post_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT character_id, name 
        FROM characters 
        WHERE user_id = ? AND status = 'approved'
        ORDER BY created_at DESC
    ''', (user_id,))
    characters = cursor.fetchall()
    conn.close()
    
    if not characters:
        await query.edit_message_text("❌ У вас нет одобренных персонажей.")
        return
    
    keyboard = []
    
    for char_id, char_name in characters:
        keyboard.append([InlineKeyboardButton(f"📝 {char_name}", callback_data=f"post_char_{char_id}")])
    
    if len(characters) == 2:
        keyboard.append([InlineKeyboardButton("📝 Пост за обоих персонажей", callback_data=f"post_both_{characters[0][0]}_{characters[1][0]}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 Выберите персонажа для написания поста:",
        reply_markup=reply_markup
    )

async def start_post_for_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    char_id = query.data.replace("post_char_", "")
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM characters WHERE character_id = ?', (char_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        await query.edit_message_text("❌ Персонаж не найден.")
        return
    
    char_name = result[0]
    user_id = query.from_user.id
    
    # Проверка кулдауна
    if not is_admin(user_id):
        if user_id in user_cooldowns:
            time_passed = time.time() - user_cooldowns[user_id]
            if time_passed < 600:
                minutes_left = int((600 - time_passed) / 60)
                await query.edit_message_text(f"⏰ Подождите еще {minutes_left} минут перед написанием следующего поста.")
                return
    
    context.user_data['post_character'] = char_id
    context.user_data['post_character_name'] = char_name
    
    if is_admin(user_id):
        # Для админов сразу начинаем писать пост
        context.user_data['post_active'] = True
        context.user_data['post_content'] = []
        
        username = query.from_user.username or "Администратор"
        await send_status_notification(context, f"📝 Администратор @{username} начал писать пост за персонажа: {char_name}")
        
        await query.edit_message_text(
            f"📝 Вы пишете пост за персонажа: {char_name}\n\n"
            "Присылайте текст поста сообщениями. Когда закончите, отправьте команду /end_post\n"
            "Для отмены используйте /cancel_post"
        )
        
        return WRITING_POST_CONTENT
    else:
        # Для обычных пользователей запрашиваем код
        await query.edit_message_text(
            f"📝 Вы пишете пост за персонажа: {char_name}\n\n"
            "Пожалуйста, введите ваш уникальный код для подтверждения:"
        )
        
        return WRITING_POST_CODE

async def start_post_for_both_characters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    char_ids = query.data.replace("post_both_", "").split("_")
    
    if len(char_ids) != 2:
        await query.edit_message_text("❌ Ошибка выбора персонажей.")
        return
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM characters WHERE character_id = ?', (char_ids[0],))
    char1 = cursor.fetchone()
    cursor.execute('SELECT name FROM characters WHERE character_id = ?', (char_ids[1],))
    char2 = cursor.fetchone()
    
    conn.close()
    
    if not char1 or not char2:
        await query.edit_message_text("❌ Один из персонажей не найден.")
        return
    
    char1_name, char2_name = char1[0], char2[0]
    user_id = query.from_user.id
    
    # Проверка кулдауна
    if not is_admin(user_id):
        if user_id in user_cooldowns:
            time_passed = time.time() - user_cooldowns[user_id]
            if time_passed < 600:
                minutes_left = int((600 - time_passed) / 60)
                await query.edit_message_text(f"⏰ Подождите еще {minutes_left} минут перед написанием следующего поста.")
                return
    
    context.user_data['post_both_characters'] = True
    context.user_data['post_characters'] = char_ids
    context.user_data['post_character_names'] = [char1_name, char2_name]
    context.user_data['post_active'] = True
    context.user_data['post_content'] = []
    
    username = query.from_user.username or query.from_user.first_name
    await send_status_notification(context, f"📝 Игрок @{username} начал писать совместный пост за персонажей: {char1_name} и {char2_name}")
    
    await query.edit_message_text(
        f"📝 Вы пишете совместный пост за персонажей: {char1_name} и {char2_name}\n\n"
        "Присылайте текст поста сообщениями. Когда закончите, отправьте команду /end_post\n"
        "Для отмены используйте /cancel_post\n\n"
        "В тексте указывайте, какой персонаж говорит или действует."
    )
    
    return WRITING_POST_CONTENT

async def post_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    entered_code = update.message.text.strip()
    character_id = context.user_data.get('post_character')
    char_name = context.user_data.get('post_character_name')
    
    logger.info(f"Пользователь {user_id} ввел код для персонажа {character_id}: {entered_code[:10]}...")
    
    if not character_id:
        await update.message.reply_text("❌ Ошибка: персонаж не найден в контексте.")
        return ConversationHandler.END
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT unique_code FROM characters 
        WHERE character_id = ? AND user_id = ? AND status = 'approved'
    ''', (character_id, user_id))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        await update.message.reply_text("❌ Ошибка: персонаж не найден в базе данных.")
        return ConversationHandler.END
    
    correct_code = result[0]
    
    logger.info(f"Сравнение кодов. Введенный: {entered_code[:20]}..., Правильный: {correct_code[:20]}...")
    
    if entered_code == correct_code:
        context.user_data['post_active'] = True
        context.user_data['post_content'] = []
        
        await update.message.reply_text(
            f"✅ Код подтвержден! Вы пишете пост за {char_name}\n\n"
            "Присылайте текст поста сообщениями. Когда закончите, отправьте команду /end_post\n"
            "Для отмены используйте /cancel_post"
        )
        
        return WRITING_POST_CONTENT
    else:
        await update.message.reply_text("❌ Неверный код. Попробуйте снова или отправьте /cancel_post для отмены:")
        return WRITING_POST_CODE

async def post_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data.setdefault('post_content', []).append(text)
    await update.message.reply_text("✅ Часть поста добавлена. Продолжайте или отправьте /end_post для завершения.")
    
    return WRITING_POST_CONTENT

async def end_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post_content = context.user_data.get('post_content', [])
    
    if not post_content:
        await update.message.reply_text("❌ Пост пуст. Добавьте текст перед завершением.")
        return ConversationHandler.END
    
    full_post = "\n".join(post_content)
    
    if context.user_data.get('post_both_characters'):
        char_ids = context.user_data.get('post_characters', [])
        char_names = context.user_data.get('post_character_names', [])
        
        combined_names = " & ".join(char_names)
        
        message_id = await send_post_to_topic(context, combined_names, full_post)
        
        for char_id in char_ids:
            conn = sqlite3.connect('nonamegame.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO posts (character_id, content, message_id) 
                VALUES (?, ?, ?)
            ''', (char_id, full_post, message_id))
            conn.commit()
            conn.close()
        
        char_names_text = " и ".join(char_names)
    else:
        character_id = context.user_data.get('post_character')
        char_name = context.user_data.get('post_character_name')
        
        message_id = await send_post_to_topic(context, char_name, full_post)
        
        conn = sqlite3.connect('nonamegame.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO posts (character_id, content, message_id) 
            VALUES (?, ?, ?)
        ''', (character_id, full_post, message_id))
        conn.commit()
        conn.close()
        
        char_names_text = char_name
    
    if not is_admin(update.effective_user.id):
        user_cooldowns[update.effective_user.id] = time.time()
    
    username = update.effective_user.username or update.effective_user.first_name
    await send_status_notification(context, f"✅ Игрок @{username} завершил пост за персонажа: {char_names_text}")
    
    # Очищаем данные
    for key in ['post_character', 'post_character_name', 'post_active', 'post_content', 
                'post_both_characters', 'post_characters', 'post_character_names']:
        context.user_data.pop(key, None)
    
    await update.message.reply_text(
        "✅ Пост успешно опубликован!" + 
        ("\nСледующий пост можно будет написать через 10 минут." if not is_admin(update.effective_user.id) else "")
    )
    
    return ConversationHandler.END

async def cancel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    char_name = context.user_data.get('post_character_name')
    
    # Очищаем данные
    for key in ['post_character', 'post_character_name', 'post_active', 'post_content', 
                'post_both_characters', 'post_characters', 'post_character_names']:
        context.user_data.pop(key, None)
    
    username = update.effective_user.username or update.effective_user.first_name
    await send_status_notification(context, f"❌ Игрок @{username} отменил пост за персонажа: {char_name}")
    
    await update.message.reply_text("❌ Написание поста отменено.")
    return ConversationHandler.END

# ========== ПОСТЫ ОТ СИСТЕМЫ И ПОМОЩНИКА ==========

async def admin_system_post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return ConversationHandler.END
    
    context.user_data['system_post_content'] = []
    
    await query.edit_message_text(
        "⚡ Вы пишете пост от имени СИСТЕМЫ\n\n"
        "Присылайте текст поста сообщениями. Когда закончите, отправьте команду /end_system_post\n"
        "Для отмены используйте /cancel_system_post"
    )
    
    return WRITING_SYSTEM_POST

async def admin_assistant_post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return ConversationHandler.END
    
    context.user_data['assistant_post_content'] = []
    
    await query.edit_message_text(
        "👨‍💼 Вы пишете пост от имени ПОМОЩНИКА СИСТЕМЫ\n\n"
        "Присылайте текст поста сообщениями. Когда закончите, отправьте команду /end_assistant_post\n"
        "Для отмены используйте /cancel_assistant_post"
    )
    
    return WRITING_ASSISTANT_POST

async def system_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data.setdefault('system_post_content', []).append(text)
    await update.message.reply_text("✅ Часть поста от системы добавлена. Продолжайте или отправьте /end_system_post для завершения.")
    
    return WRITING_SYSTEM_POST

async def assistant_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data.setdefault('assistant_post_content', []).append(text)
    await update.message.reply_text("✅ Часть поста от помощника добавлена. Продолжайте или отправьте /end_assistant_post для завершения.")
    
    return WRITING_ASSISTANT_POST

async def end_system_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post_content = context.user_data.get('system_post_content', [])
    
    if not post_content:
        await update.message.reply_text("❌ Пост пуст. Добавьте текст перед завершением.")
        return ConversationHandler.END
    
    full_post = "\n".join(post_content)
    
    message_id = await send_post_to_topic(context, "СИСТЕМА", full_post, 'system')
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO posts (character_id, content, post_type, message_id) 
        VALUES (?, ?, ?, ?)
    ''', ('SYSTEM', full_post, 'system', message_id))
    conn.commit()
    conn.close()
    
    username = update.effective_user.username or update.effective_user.first_name
    await send_status_notification(context, f"⚡ Администратор @{username} опубликовал пост от системы")
    
    context.user_data.pop('system_post_content', None)
    
    await update.message.reply_text("✅ Пост от системы успешно опубликован!")
    return ConversationHandler.END

async def end_assistant_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post_content = context.user_data.get('assistant_post_content', [])
    
    if not post_content:
        await update.message.reply_text("❌ Пост пуст. Добавьте текст перед завершением.")
        return ConversationHandler.END
    
    full_post = "\n".join(post_content)
    
    message_id = await send_post_to_topic(context, "ПОМОЩНИК СИСТЕМЫ", full_post, 'assistant')
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO posts (character_id, content, post_type, message_id) 
        VALUES (?, ?, ?, ?)
    ''', ('ASSISTANT', full_post, 'assistant', message_id))
    conn.commit()
    conn.close()
    
    username = update.effective_user.username or update.effective_user.first_name
    await send_status_notification(context, f"👨‍💼 Администратор @{username} опубликовал пост от помощника системы")
    
    context.user_data.pop('assistant_post_content', None)
    
    await update.message.reply_text("✅ Пост от помощника системы успешно опубликован!")
    return ConversationHandler.END

async def cancel_system_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('system_post_content', None)
    
    username = update.effective_user.username or update.effective_user.first_name
    await send_status_notification(context, f"❌ Администратор @{username} отменил пост от системы")
    
    await update.message.reply_text("❌ Написание поста от системы отменено.")
    return ConversationHandler.END

async def cancel_assistant_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('assistant_post_content', None)
    
    username = update.effective_user.username or update.effective_user.first_name
    await send_status_notification(context, f"❌ Администратор @{username} отменил пост от помощника системы")
    
    await update.message.reply_text("❌ Написание поста от помощника системы отменено.")
    return ConversationHandler.END

# ========== АДМИНСКИЕ ФУНКЦИИ ==========

async def show_my_characters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, race, class, status, decline_reason, character_id
        FROM characters WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (user_id,))
    characters = cursor.fetchall()
    conn.close()
    
    if not characters:
        await query.edit_message_text("❌ У вас пока нет персонажей.")
        return
    
    text = "🎭 Ваши персонажи:\n\n"
    for char in characters:
        name, race, char_class, status, decline_reason, char_id = char
        
        if status == 'approved':
            status_text = "✅ Одобрен"
            char_info = f" (ID: {char_id})"
        elif status == 'declined':
            status_text = f"❌ Отклонен - {decline_reason}"
            char_info = ""
        else:
            status_text = "⏳ На проверке"
            char_info = ""
        
        text += f"{status_text}\n📛 {name} - {race} {char_class}{char_info}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    keyboard = [
        [InlineKeyboardButton("👁️ Проверить анкеты", callback_data="admin_review")],
        [InlineKeyboardButton("🗑️ Удалить персонажа", callback_data="admin_delete_char")],
        [InlineKeyboardButton("⚙️ Настройки чатов", callback_data="admin_settings")],
        [InlineKeyboardButton("📦 Управление предметами", callback_data="admin_items_menu")],
        [InlineKeyboardButton("⚔️ Управление навыками", callback_data="admin_skills_menu")],
        [InlineKeyboardButton("📊 Редактировать статы", callback_data="admin_edit_stats")],
        [InlineKeyboardButton("📈 Статистики всех игроков", callback_data="admin_all_stats")],
        [InlineKeyboardButton("⚡ Написать от системы", callback_data="admin_system_post")],
        [InlineKeyboardButton("👨‍💼 Написать от помощника", callback_data="admin_assistant_post")]
    ]
    
    if is_super_admin(user_id):
        keyboard.append([InlineKeyboardButton("👥 Управление админами", callback_data="admin_manage_admins")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("⚙️ Панель администратора:", reply_markup=reply_markup)

async def show_pending_characters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.name, c.race, c.class, c.user_id, u.username 
        FROM characters c 
        LEFT JOIN users u ON c.user_id = u.user_id 
        WHERE c.status = 'pending'
    ''')
    pending_chars = cursor.fetchall()
    conn.close()
    
    if not pending_chars:
        await query.edit_message_text("✅ Нет анкет на проверку.")
        return
    
    char_id, name, race, char_class, user_id, username = pending_chars[0]
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT age_height, backstory, appearance FROM characters WHERE id = ?', (char_id,))
    char_details = cursor.fetchone()
    conn.close()
    
    age_height, backstory, appearance = char_details
    
    text = (
        f"📝 Анкета на проверку\n\n"
        f"👤 Игрок: @{username} (ID: {user_id})\n"
        f"📛 Имя: {name}\n"
        f"🏹 Раса: {race}\n"
        f"⚔️ Класс: {char_class}\n"
        f"📏 Возраст/рост: {age_height}\n"
        f"📖 Предыстория: {backstory}\n"
        f"👀 Внешность: {appearance}\n\n"
        f"🆔 ID анкеты: {char_id}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{char_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{char_id}")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def approve_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    char_id = int(query.data.replace("approve_", ""))
    
    await query.answer("Одобряем персонажа...")
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    unique_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(196))
    character_id = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(3))
    
    cursor.execute('''
        SELECT c.user_id, c.name, c.age_height, c.race, c.class, c.backstory, c.appearance, u.username,
               c.character_photo_id 
        FROM characters c 
        LEFT JOIN users u ON c.user_id = u.user_id 
        WHERE c.id = ?
    ''', (char_id,))
    char_data = cursor.fetchone()
    
    if not char_data:
        conn.close()
        return
        
    user_id, char_name, age_height, race, char_class, backstory, appearance, username, photo_id = char_data
    
    cursor.execute('''
        UPDATE characters 
        SET status = 'approved', unique_code = ?, character_id = ?
        WHERE id = ?
    ''', (unique_code, character_id, char_id))
    
    conn.commit()
    conn.close()
    
    try:
        await context.bot.send_message(
            user_id,
            f"🎉 Ваш персонаж '{char_name}' одобрен!\n\n"
            f"📋 Ваш уникальный код (сохраните!):\n{unique_code}\n\n"
            f"🆔 ID персонажа: {character_id}\n\n"
            "Используйте код при написании первого поста."
        )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение игроку {user_id}: {e}")
    
    public_caption = f"""<b>🎭 НОВЫЙ ПЕРСОНАЖ ОДОБРЕН</b>

<b>👤 Игрок:</b> @{username}
<b>📛 Имя:</b> {char_name}
<b>🏹 Раса:</b> {race}
<b>⚔️ Класс:</b> {char_class}
<b>📏 Возраст/рост:</b> {age_height}
<b>📖 Предыстория:</b> {backstory}
<b>👀 Внешность:</b> {appearance}

<b>🆔 ID персонажа:</b> {character_id}
<b>✅ Статус:</b> Одобрен"""
    
    characters_setting = get_chat_setting('characters')
    if characters_setting:
        chat_id, thread_id = characters_setting
        if photo_id and len(public_caption) <= 1024:
            await context.bot.send_photo(
                chat_id=chat_id,
                message_thread_id=thread_id,
                photo=photo_id,
                caption=public_caption,
                parse_mode='HTML'
            )
        else:
            if photo_id:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    photo=photo_id,
                    parse_mode='HTML'
                )
            await context.bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=public_caption,
                parse_mode='HTML'
            )
    
    await query.edit_message_reply_markup(reply_markup=None)
    await query.edit_message_text(f"✅ Персонаж '{char_name}' одобрен! ID: {character_id}")

async def reject_character_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    char_id = int(query.data.replace("reject_", ""))
    await query.answer()
    
    context.user_data['rejecting_char_id'] = char_id
    
    await query.edit_message_text("Введите причину отказа для этой анкеты:")
    
    return REJECTING_CHAR

async def reject_character_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    char_id = context.user_data.get('rejecting_char_id')
    reason = update.message.text
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, name FROM characters WHERE id = ?', (char_id,))
    result = cursor.fetchone()
    
    if not result:
        await update.message.reply_text("❌ Ошибка: персонаж не найден.")
        conn.close()
        return ConversationHandler.END
        
    user_id, char_name = result
    
    cursor.execute('''
        UPDATE characters 
        SET status = 'declined', decline_reason = ?
        WHERE id = ?
    ''', (reason, char_id))
    
    conn.commit()
    conn.close()
    
    try:
        await context.bot.send_message(
            user_id,
            f"❌ Ваш персонаж '{char_name}' был отклонен.\n\n"
            f"📝 Причина: {reason}\n\n"
            "Вы можете создать нового персонажа с помощью /start"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
    
    await update.message.reply_text(f"❌ Персонаж отклонен. Причина отправлена игроку.")
    
    context.user_data.pop('rejecting_char_id', None)
    
    return ConversationHandler.END

async def show_character_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, race, class, level, exp, health, mana, 
               strength, speed, agility, control, skill_points, hc_coins, character_id,
               fire_affinity, water_affinity, air_affinity, earth_affinity,
               dark_affinity, light_affinity, life_affinity, death_affinity,
               group_name, achievements
        FROM characters 
        WHERE user_id = ? AND status = 'approved'
    ''', (user_id,))
    characters = cursor.fetchall()
    
    if not characters:
        conn.close()
        await query.edit_message_text("❌ У вас нет одобренных персонажей.")
        return
    
    char_data = characters[0]
    (name, race, char_class, level, exp, health, mana, 
     strength, speed, agility, control, skill_points, hc_coins, char_id,
     fire_affinity, water_affinity, air_affinity, earth_affinity,
     dark_affinity, light_affinity, life_affinity, death_affinity,
     group_name, achievements) = char_data
    
    level_progress = get_level_progress(exp, level)
    
    # Получаем предметы
    cursor.execute('SELECT item_name, item_type, quantity FROM items WHERE character_id = ?', (char_id,))
    items = cursor.fetchall()
    
    # Получаем активные навыки
    cursor.execute('''
        SELECT skill_name FROM skills 
        WHERE character_id = ? AND skill_type = 'Активный'
    ''', (char_id,))
    active_skills = cursor.fetchall()
    
    # Получаем пассивные навыки
    cursor.execute('''
        SELECT skill_name FROM skills 
        WHERE character_id = ? AND skill_type = 'Пассивный'
    ''', (char_id,))
    passive_skills = cursor.fetchall()
    
    conn.close()
    
    # Формируем список предметов
    items_text = "Пусто"
    if items:
        items_list = [f"{item_name} ({item_type}) x{quantity}" for item_name, item_type, quantity in items]
        items_text = ", ".join(items_list)
    
    # Формируем список активных навыков
    active_skills_text = "«Нет»"
    if active_skills:
        active_skills_list = [f"«{skill[0]}»" for skill in active_skills]
        active_skills_text = ", ".join(active_skills_list)
    
    # Формируем список пассивных навыков
    passive_skills_list = ["«Тело игрока»", "«Разум игрока»"]
    if passive_skills:
        passive_skills_list.extend([f"«{skill[0]}»" for skill in passive_skills])
    passive_skills_text = ", ".join(passive_skills_list)
    
    stats_text = f"""
👤 {name} (ID: {char_id})
- Класс: {char_class}
- Раса: {race}
Уровень: {level} ({level_progress} EXP)

– Характеристики –

×Здоровье: {health} | HP
×Мана: {mana} | MP
×Регенерация здоровья: {health//10}/мин | маны: {mana//10}/мин

× Сила: {strength}
× Скорость: {speed}
× Ловкость и выносливость: {agility}
× Контроль: {control}

Родство со стихиями:
Огонь: {fire_affinity:.3f}% (Магия огня)
Вода: {water_affinity:.3f}% (Магия воды)
Воздух: {air_affinity:.3f}% (Магия воздуха)
Земля: {earth_affinity:.3f}% (Магия земли)
Тьма: {dark_affinity:.6f}% (Магия тьмы)
Свет: {light_affinity:.5f}% (Магия света)
Жизнь: {life_affinity:.5f}% (Магия жизни)
Смерть: {death_affinity:.7f}% (Некромантия)

Очки характеристики: {skill_points}
Очки навыков: 0
ХК: {hc_coins}

Группа: {group_name}

Достижения: {achievements}

Активные навыки: {active_skills_text}

Пассивные навыки:
{passive_skills_text}

Экипировано: Пусто

Инвентарь: {items_text}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

async def show_character_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, race, class, level, exp, health, mana, 
               strength, speed, agility, control, skill_points, hc_coins, character_id,
               fire_affinity, water_affinity, air_affinity, earth_affinity,
               dark_affinity, light_affinity, life_affinity, death_affinity,
               group_name, achievements
        FROM characters 
        WHERE user_id = ? AND status = 'approved'
    ''', (user_id,))
    characters = cursor.fetchall()
    conn.close()
    
    if not characters:
        await query.edit_message_text("❌ У вас нет одобренных персонажей.")
        return
    
    char_data = characters[0]
    (name, race, char_class, level, exp, health, mana, 
     strength, speed, agility, control, skill_points, hc_coins, char_id,
     fire_affinity, water_affinity, air_affinity, earth_affinity,
     dark_affinity, light_affinity, life_affinity, death_affinity,
     group_name, achievements) = char_data
    
    level_progress = get_level_progress(exp, level)
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('SELECT item_name, quantity FROM items WHERE character_id = ?', (char_id,))
    items = cursor.fetchall()
    conn.close()
    
    items_text = "Пусто"
    if items:
        items_list = [f"{item_name} (x{quantity})" for item_name, quantity in items]
        items_text = ", ".join(items_list)
    
    stats_text = f"""
👤 {name} (ID: {char_id})
• Класс: {char_class}
• Раса: {race}
Уровень: {level} ({level_progress} EXP)

– Характеристики –

×Здоровье: {health} | HP
×Мана: {mana} | MP
×Регенерация здоровья: {health//10}/мин | маны: {mana//10}/мин

× Сила: {strength}
× Скорость: {speed}
× Ловкость и выносливость: {agility}
× Контроль: {control}

Родство со стихиями:
Огонь: {fire_affinity:.3f}% (Магия огня)
Вода: {water_affinity:.3f}% (Магия воды)
Воздух: {air_affinity:.3f}% (Магия воздуха)
Земля: {earth_affinity:.3f}% (Магия земли)
Тьма: {dark_affinity:.6f}% (Магия тьмы)
Свет: {light_affinity:.5f}% (Магия света)
Жизнь: {life_affinity:.5f}% (Магия жизни)
Смерть: {death_affinity:.7f}% (Некромантия)

Очки характеристики: {skill_points}
Очки навыков: 0
ХК: {hc_coins}

Группа: {group_name}

Достижения: {achievements}

Активные навыки: «Нет»

Пассивные навыки:
«Тело игрока», «Разум игрока»

Экипировано: Пусто

Инвентарь: {items_text}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

async def show_stats_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку по характеристикам"""
    query = update.callback_query
    await query.answer()
    
    guide_text = get_stats_explanation()
    
    keyboard = [[InlineKeyboardButton("📙 Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(guide_text, reply_markup=reply_markup, parse_mode='HTML')

async def upgrade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, character_id, skill_points, strength, speed, agility, control, health, mana, level, exp
        FROM characters 
        WHERE user_id = ? AND status = 'approved'
    ''', (user_id,))
    characters = cursor.fetchall()
    conn.close()
    
    if not characters:
        await query.edit_message_text("❌ У вас нет одобренных персонажей.")
        return
    
    char_name, char_id, skill_points, strength, speed, agility, control, health, mana, level, exp = characters[0]
    
    if skill_points <= 0:
        keyboard = [
            [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ У вашего персонажа '{char_name}' нет очков характеристики для прокачки.\n\n"
            "Ожидайте получения очков от администрации.",
            reply_markup=reply_markup
        )
        return
    
    stat_bonus = 2 if level < 15 else 1
    affinity_bonus = 1.0 if level < 15 else 0.5
    
    level_progress = get_level_progress(exp, level)
    
    text = f"""
⚡ Прокачка персонажа: {char_name} (Уровень: {level}, {level_progress} EXP)

Доступно очков характеристики: {skill_points}

📊 Бонусы за уровень {level}:
• +{stat_bonus} к характеристике за 1 очко
• +{affinity_bonus}% к родству со стихией за 1 очко

Текущие характеристики:
× Сила: {strength}
× Скорость: {speed} 
× Ловкость: {agility}
× Контроль: {control}
× Здоровье: {health}
× Мана: {mana}

Выберите характеристику для улучшения:
"""
    
    keyboard = [
        [InlineKeyboardButton(f"💪 Сила (+{stat_bonus}) - сейчас {strength}", callback_data="upgrade_strength")],
        [InlineKeyboardButton(f"⚡ Скорость (+{stat_bonus}) - сейчас {speed}", callback_data="upgrade_speed")],
        [InlineKeyboardButton(f"🏃 Ловкость (+{stat_bonus}) - сейчас {agility}", callback_data="upgrade_agility")],
        [InlineKeyboardButton(f"🎯 Контроль (+{stat_bonus}) - сейчас {control}", callback_data="upgrade_control")],
        [InlineKeyboardButton(f"❤️ Здоровье (+{stat_bonus * 10}) - сейчас {health}", callback_data="upgrade_health")],
        [InlineKeyboardButton(f"🔵 Мана (+{stat_bonus * 10}) - сейчас {mana}", callback_data="upgrade_mana")],
        [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    upgrade_type = query.data.replace("upgrade_", "")
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, character_id, skill_points, strength, speed, agility, control, health, mana, level, exp,
               fire_affinity, water_affinity, air_affinity, earth_affinity
        FROM characters 
        WHERE user_id = ? AND status = 'approved'
    ''', (user_id,))
    character = cursor.fetchone()
    
    if not character:
        await query.edit_message_text("❌ Персонаж не найден.")
        return
    
    (char_id, char_name, character_id, skill_points, strength, speed, agility, control, health, mana, level, exp,
     fire_affinity, water_affinity, air_affinity, earth_affinity) = character
    
    if skill_points <= 0:
        await query.edit_message_text("❌ Недостаточно очков характеристики!")
        conn.close()
        return
    
    stat_bonus = 2 if level < 15 else 1
    affinity_bonus = 1.0 if level < 15 else 0.5
    
    if upgrade_type == "strength":
        cursor.execute('UPDATE characters SET strength = strength + ?, skill_points = skill_points - 1 WHERE id = ?', (stat_bonus, char_id))
        new_value = strength + stat_bonus
    elif upgrade_type == "speed":
        cursor.execute('UPDATE characters SET speed = speed + ?, skill_points = skill_points - 1 WHERE id = ?', (stat_bonus, char_id))
        new_value = speed + stat_bonus
    elif upgrade_type == "agility":
        cursor.execute('UPDATE characters SET agility = agility + ?, skill_points = skill_points - 1 WHERE id = ?', (stat_bonus, char_id))
        new_value = agility + stat_bonus
    elif upgrade_type == "control":
        cursor.execute('UPDATE characters SET control = control + ?, skill_points = skill_points - 1 WHERE id = ?', (stat_bonus, char_id))
        new_value = control + stat_bonus
    elif upgrade_type == "health":
        health_bonus = stat_bonus * 10
        cursor.execute('UPDATE characters SET health = health + ?, skill_points = skill_points - 1 WHERE id = ?', (health_bonus, char_id))
        new_value = health + health_bonus
    elif upgrade_type == "mana":
        mana_bonus = stat_bonus * 10
        cursor.execute('UPDATE characters SET mana = mana + ?, skill_points = skill_points - 1 WHERE id = ?', (mana_bonus, char_id))
        new_value = mana + mana_bonus
    else:
        await query.edit_message_text("❌ Неизвестный тип прокачки.")
        conn.close()
        return
    
    cursor.execute('''
        UPDATE characters SET 
        fire_affinity = fire_affinity + ?,
        water_affinity = water_affinity + ?,
        air_affinity = air_affinity + ?,
        earth_affinity = earth_affinity + ?
        WHERE id = ?
    ''', (affinity_bonus/100, affinity_bonus/100, affinity_bonus/100, affinity_bonus/100, char_id))
    
    conn.commit()
    conn.close()
    
    stat_names = {
        "strength": "💪 Сила",
        "speed": "⚡ Скорость", 
        "agility": "🏃 Ловкость",
        "control": "🎯 Контроль",
        "health": "❤️ Здоровье",
        "mana": "🔵 Мана"
    }
    
    skill_points -= 1
    
    keyboard = [
        [InlineKeyboardButton(f"💪 Сила (+{stat_bonus}) - сейчас {new_value if upgrade_type == 'strength' else strength}", callback_data="upgrade_strength")],
        [InlineKeyboardButton(f"⚡ Скорость (+{stat_bonus}) - сейчас {new_value if upgrade_type == 'speed' else speed}", callback_data="upgrade_speed")],
        [InlineKeyboardButton(f"🏃 Ловкость (+{stat_bonus}) - сейчас {new_value if upgrade_type == 'agility' else agility}", callback_data="upgrade_agility")],
        [InlineKeyboardButton(f"🎯 Контроль (+{stat_bonus}) - сейчас {new_value if upgrade_type == 'control' else control}", callback_data="upgrade_control")],
        [InlineKeyboardButton(f"❤️ Здоровье (+{stat_bonus * 10}) - сейчас {new_value if upgrade_type == 'health' else health}", callback_data="upgrade_health")],
        [InlineKeyboardButton(f"🔵 Мана (+{stat_bonus * 10}) - сейчас {new_value if upgrade_type == 'mana' else mana}", callback_data="upgrade_mana")],
        [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
✅ Характеристика {stat_names[upgrade_type]} улучшена!
📊 Новое значение: {new_value}
🎯 Осталось очков: {skill_points}
✨ Родство со стихиями увеличено на +{affinity_bonus}%

⚡ Продолжайте прокачку или вернитесь в меню:

Текущие характеристики:
× Сила: {new_value if upgrade_type == 'strength' else strength}
× Скорость: {new_value if upgrade_type == 'speed' else speed} 
× Ловкость: {new_value if upgrade_type == 'agility' else agility}
× Контроль: {new_value if upgrade_type == 'control' else control}
× Здоровье: {new_value if upgrade_type == 'health' else health}
× Мана: {new_value if upgrade_type == 'mana' else mana}
"""
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def admin_give_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🎁 Выдача предмета персонажу\n\n"
        "Введите данные в формате:\n"
        "<ID_персонажа> <название_предмета> <количество>\n\n"
        "Пример: ABC Меч_огня 1\n\n"
        "Для отмены введите /cancel"
    )
    
    return GIVING_ITEM

async def give_item_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == '/cancel':
        await update.message.reply_text("❌ Выдача предмета отменена.")
        return ConversationHandler.END
    
    parts = text.split()
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ Неверный формат!\n\n"
            "Используйте: <ID_персонажа> <название_предмета> <количество>\n"
            "Пример: ABC Меч_огня 1"
        )
        return GIVING_ITEM
    
    character_id = parts[0]
    item_name = ' '.join(parts[1:-1])
    quantity = parts[-1]
    
    try:
        quantity = int(quantity)
    except ValueError:
        await update.message.reply_text("❌ Количество должно быть числом!")
        return GIVING_ITEM
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name, user_id FROM characters WHERE character_id = ?', (character_id,))
    character = cursor.fetchone()
    
    if not character:
        await update.message.reply_text("❌ Персонаж с таким ID не найден.")
        conn.close()
        return ConversationHandler.END
    
    char_name, target_user_id = character
    
    cursor.execute('''
        INSERT INTO items (character_id, item_name, quantity)
        VALUES (?, ?, ?)
    ''', (character_id, item_name, quantity))
    
    conn.commit()
    conn.close()
    
    try:
        await context.bot.send_message(
            target_user_id,
            f"🎁 Вы получили новый предмет!\n\n"
            f"📦 Предмет: {item_name}\n"
            f"📊 Количество: {quantity}\n"
            f"👤 Персонаж: {char_name}\n\n"
            f"🆔 ID персонажа: {character_id}"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")
    
    await update.message.reply_text(
        f"✅ Предмет '{item_name}' (x{quantity}) выдан персонажу {char_name} (ID: {character_id})"
    )
    
    return ConversationHandler.END

async def admin_edit_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT character_id, name, level, group_name, achievements 
        FROM characters 
        WHERE status = 'approved'
        ORDER BY created_at DESC
        LIMIT 20
    ''')
    characters = cursor.fetchall()
    conn.close()
    
    if not characters:
        await query.edit_message_text("❌ Нет одобренных персонажей.")
        return
    
    keyboard = []
    for char_id, name, level, group_name, achievements in characters:
        button_text = f"{name} (Ур. {level}) - {char_id}"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"edit_{char_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📊 Редактирование характеристик персонажа:\n\n"
        "Выберите персонажа для редактирования:",
        reply_markup=reply_markup
    )

async def admin_edit_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    character_id = query.data.replace("edit_", "")
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT name, level, health, mana, strength, speed, agility, control,
               skill_points, hc_coins, fire_affinity, water_affinity, air_affinity,
               earth_affinity, dark_affinity, light_affinity, life_affinity, death_affinity,
               group_name, achievements
        FROM characters WHERE character_id = ? AND status = 'approved'
    ''', (character_id,))
    character = cursor.fetchone()
    conn.close()
    
    if not character:
        await query.edit_message_text(f"❌ Персонаж не найден. ID: {character_id}")
        return
    
    (name, level, health, mana, strength, speed, agility, control,
     skill_points, hc_coins, fire_affinity, water_affinity, air_affinity,
     earth_affinity, dark_affinity, light_affinity, life_affinity, death_affinity,
     group_name, achievements) = character
    
    context.user_data['editing_char_id'] = character_id
    context.user_data['editing_char_name'] = name
    
    keyboard = [
        [InlineKeyboardButton(f"📊 Уровень: {level}", callback_data=f"edit_level_{character_id}")],
        [InlineKeyboardButton(f"❤️ Здоровье: {health}", callback_data=f"edit_health_{character_id}")],
        [InlineKeyboardButton(f"🔵 Мана: {mana}", callback_data=f"edit_mana_{character_id}")],
        [InlineKeyboardButton(f"💪 Сила: {strength}", callback_data=f"edit_strength_{character_id}")],
        [InlineKeyboardButton(f"⚡ Скорость: {speed}", callback_data=f"edit_speed_{character_id}")],
        [InlineKeyboardButton(f"🏃 Ловкость: {agility}", callback_data=f"edit_agility_{character_id}")],
        [InlineKeyboardButton(f"🎯 Контроль: {control}", callback_data=f"edit_control_{character_id}")],
        [InlineKeyboardButton(f"🎯 Очки характеристик: {skill_points}", callback_data=f"edit_skill_points_{character_id}")],
        [InlineKeyboardButton(f"💰 ХК: {hc_coins}", callback_data=f"edit_hc_coins_{character_id}")],
        [InlineKeyboardButton(f"🔥 Огонь: {fire_affinity:.3f}%", callback_data=f"edit_fire_{character_id}")],
        [InlineKeyboardButton(f"💧 Вода: {water_affinity:.3f}%", callback_data=f"edit_water_{character_id}")],
        [InlineKeyboardButton(f"💨 Воздух: {air_affinity:.3f}%", callback_data=f"edit_air_{character_id}")],
        [InlineKeyboardButton(f"🌍 Земля: {earth_affinity:.3f}%", callback_data=f"edit_earth_{character_id}")],
        [InlineKeyboardButton(f"🌑 Тьма: {dark_affinity:.6f}%", callback_data=f"edit_dark_{character_id}")],
        [InlineKeyboardButton(f"✨ Свет: {light_affinity:.5f}%", callback_data=f"edit_light_{character_id}")],
        [InlineKeyboardButton(f"💚 Жизнь: {life_affinity:.5f}%", callback_data=f"edit_life_{character_id}")],
        [InlineKeyboardButton(f"💀 Смерть: {death_affinity:.7f}%", callback_data=f"edit_death_{character_id}")],
        [InlineKeyboardButton(f"👥 Группа: {group_name}", callback_data=f"edit_group_{character_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_edit_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"📊 Редактирование персонажа: {name} (ID: {character_id})\n\nВыберите параметр для изменения:"
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_edit_parameter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    
    parts = data.split('_')
    if len(parts) < 3:
        logger.error(f"Неверный формат данных: {data}")
        await query.edit_message_text("❌ Ошибка формата данных")
        return
    
    param = parts[1]
    character_id = parts[2]
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    if param in ['fire', 'water', 'air', 'earth', 'dark', 'light', 'life', 'death']:
        column_name = f"{param}_affinity"
    else:
        column_name = param
    
    cursor.execute(f'SELECT name, {column_name} FROM characters WHERE character_id = ?', (character_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        await query.edit_message_text("❌ Персонаж не найден.")
        return
    
    char_name, current_value = result
    
    context.user_data['editing_param'] = param
    context.user_data['editing_char_id'] = character_id
    context.user_data['editing_char_name'] = char_name
    
    param_names = {
        'level': '📊 Уровень',
        'health': '❤️ Здоровье', 
        'mana': '🔵 Мана',
        'strength': '💪 Сила',
        'speed': '⚡ Скорость',
        'agility': '🏃 Ловкость',
        'control': '🎯 Контроль',
        'skill_points': '🎯 Очки характеристик',
        'hc_coins': '💰 ХК',
        'fire': '🔥 Огонь',
        'water': '💧 Вода',
        'air': '💨 Воздух',
        'earth': '🌍 Земля',
        'dark': '🌑 Тьма',
        'light': '✨ Свет',
        'life': '💚 Жизнь',
        'death': '💀 Смерть',
        'group': '👥 Группа'
    }
    
    param_name = param_names.get(param, param)
    
    await query.edit_message_text(
        f"✏️ Редактирование: {param_name}\n\n"
        f"👤 Персонаж: {char_name}\n"
        f"🆔 ID: {character_id}\n"
        f"📊 Текущее значение: {current_value}\n\n"
        f"Введите новое значение:\n\n"
        f"Для отмены введите /cancel"
    )
    
    return EDITING_PARAM

async def edit_param_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    param = context.user_data.get('editing_param')
    character_id = context.user_data.get('editing_char_id')
    char_name = context.user_data.get('editing_char_name', 'Неизвестно')
    new_value = update.message.text
    
    if new_value == '/cancel':
        await update.message.reply_text("❌ Редактирование отменено.")
        context.user_data.pop('editing_param', None)
        context.user_data.pop('editing_char_id', None)
        context.user_data.pop('editing_char_name', None)
        return ConversationHandler.END
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    try:
        if param in ['level', 'health', 'mana', 'strength', 'speed', 'agility', 'control', 'skill_points', 'hc_coins']:
            new_value_int = int(new_value)
            if new_value_int < 0:
                raise ValueError("Значение не может быть отрицательным")
            cursor.execute(f'UPDATE characters SET {param} = ? WHERE character_id = ?', 
                         (new_value_int, character_id))
        
        elif param in ['fire', 'water', 'air', 'earth', 'dark', 'light', 'life', 'death']:
            new_value_float = float(new_value)
            if new_value_float < 0:
                raise ValueError("Значение не может быть отрицательным")
            cursor.execute(f'UPDATE characters SET {param}_affinity = ? WHERE character_id = ?', 
                         (new_value_float, character_id))
        
        elif param == 'group':
            cursor.execute(f'UPDATE characters SET group_name = ? WHERE character_id = ?', 
                         (new_value, character_id))
        
        conn.commit()
        conn.close()
        
        # Создаём кнопку для возврата к редактированию
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать ещё", callback_data=f"edit_{character_id}")],
            [InlineKeyboardButton("🔙 К списку персонажей", callback_data="admin_edit_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Параметр успешно обновлен для персонажа {char_name}!",
            reply_markup=reply_markup
        )
        
        context.user_data.pop('editing_param', None)
        # НЕ очищаем editing_char_id и editing_char_name
        context.user_data.pop('editing_char_id', None)
        context.user_data.pop('editing_char_name', None)
        
    except ValueError as e:
        conn.close()
        error_msg = str(e)
        if "invalid literal" in error_msg:
            error_msg = "Неверный формат числа"
        await update.message.reply_text(f"❌ Ошибка: {error_msg}")
        return EDITING_PARAM
    except Exception as e:
        conn.close()
        logger.error(f"Ошибка обновления параметра {param}: {e}")
        await update.message.reply_text(f"❌ Ошибка обновления: {str(e)[:100]}")
        return EDITING_PARAM
    
    return ConversationHandler.END

async def delete_character_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.character_id, c.name, c.race, c.class, u.username 
        FROM characters c 
        LEFT JOIN users u ON c.user_id = u.user_id 
        WHERE c.status = 'approved'
        ORDER BY c.created_at DESC
        LIMIT 20
    ''')
    characters = cursor.fetchall()
    conn.close()
    
    if not characters:
        await query.edit_message_text("❌ Нет одобренных персонажей для удаления.")
        return
    
    keyboard = []
    for char_id, name, race, char_class, username in characters:
        button_text = f"{name} ({char_id}) - @{username}"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"delete_char_{char_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🗑️ Выберите персонажа для удаления:\n\n"
        "Формат: Имя (ID персонажа) - @игрок",
        reply_markup=reply_markup
    )

async def confirm_delete_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    char_id = query.data.replace("delete_char_", "")
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.name, c.race, c.class, u.username, u.user_id 
        FROM characters c 
        LEFT JOIN users u ON c.user_id = u.user_id 
        WHERE c.character_id = ?
    ''', (char_id,))
    character = cursor.fetchone()
    conn.close()
    
    if not character:
        await query.edit_message_text("❌ Персонаж не найден.")
        return
    
    name, race, char_class, username, user_id = character
    
    context.user_data['deleting_char_id'] = char_id
    context.user_data['deleting_char_name'] = name
    context.user_data['deleting_user_id'] = user_id
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{char_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data="admin_delete_char")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ Вы уверены, что хотите удалить персонажа?\n\n"
        f"📛 Имя: {name}\n"
        f"🏹 Раса: {race}\n"
        f"⚔️ Класс: {char_class}\n"
        f"👤 Игрок: @{username} (ID: {user_id})\n"
        f"🆔 ID персонажа: {char_id}\n\n"
        "Это действие нельзя отменить!",
        reply_markup=reply_markup
    )

async def execute_delete_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    char_id = context.user_data.get('deleting_char_id')
    char_name = context.user_data.get('deleting_char_name')
    target_user_id = context.user_data.get('deleting_user_id')
    
    if not char_id:
        await query.edit_message_text("❌ Ошибка: данные удаления не найдены.")
        return
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM characters WHERE character_id = ?', (char_id,))
    cursor.execute('DELETE FROM posts WHERE character_id = ?', (char_id,))
    cursor.execute('DELETE FROM items WHERE character_id = ?', (char_id,))
    
    conn.commit()
    conn.close()
    
    try:
        await context.bot.send_message(
            target_user_id,
            f"❌ Ваш персонаж '{char_name}' был удален администратором.\n\n"
            f"🆔 ID персонажа: {char_id}\n\n"
            "Вы можете создать нового персонажа с помощью /start"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")
    
    await send_character_notification(context, f"🗑️ Персонаж удален: {char_name} (ID: {char_id})")
    
    context.user_data['deleting_char_id'] = None
    context.user_data['deleting_char_name'] = None
    context.user_data['deleting_user_id'] = None
    
    await query.edit_message_text(f"✅ Персонаж '{char_name}' успешно удален!")

async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    await show_settings(update, context)

async def admin_all_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    conn = sqlite3.connect('nonamegame.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.character_id, c.name, c.race, c.class, c.level, c.exp, 
               u.username, u.user_id
        FROM characters c
        LEFT JOIN users u ON c.user_id = u.user_id
        WHERE c.status = 'approved'
        ORDER BY c.level DESC, c.exp DESC
    ''')
    characters = cursor.fetchall()
    conn.close()
    
    if not characters:
        await query.edit_message_text("❌ Нет одобренных персонажей.")
        return
    
    context.user_data['all_stats_index'] = 0
    context.user_data['all_stats_list'] = characters
    
    await send_next_stat(update, context)

async def send_next_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if 'all_stats_list' not in context.user_data or 'all_stats_index' not in context.user_data:
        return
    
    characters = context.user_data['all_stats_list']
    index = context.user_data['all_stats_index']
    
    if index >= len(characters):
        await query.edit_message_text("✅ Все статистики отправлены!")
        return
    
    char_id, name, race, char_class, level, exp, username, user_id = characters[index]
    
    level_progress = get_level_progress(exp, level)
    
    stat_text = f"""
👤 {name} (ID: {char_id})
• Игрок: @{username} (ID: {user_id})
• Класс: {char_class}
• Раса: {race}
• Уровень: {level} ({level_progress} EXP)
"""
    
    keyboard = [[InlineKeyboardButton("➡️ Следующий", callback_data="admin_next_stat")]]
    
    if index == len(characters) - 1:
        keyboard = [[InlineKeyboardButton("✅ Завершить", callback_data="admin_panel")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if index == 0:
        await query.edit_message_text(stat_text, reply_markup=reply_markup)
    else:
        await query.edit_message_text(stat_text, reply_markup=reply_markup)
    
    context.user_data['all_stats_index'] = index + 1

async def admin_manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_super_admin(user_id):
        await query.edit_message_text("❌ Только супер-админ может управлять админами.")
        return
    
    admins = get_admins()
    
    text = "👥 Список администраторов:\n\n"
    for admin_id, admin_username, role in admins:
        role_text = "🔴 Супер-админ" if role == 'super_admin' else "🔵 Админ"
        text += f"{role_text}: @{admin_username} (ID: {admin_id})\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin_menu")],
        [InlineKeyboardButton("➖ Удалить админа", callback_data="remove_admin_menu")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_super_admin(user_id):
        await query.edit_message_text("❌ Только супер-админ может добавлять админов.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "➕ Добавление администратора\n\n"
        "Введите ID пользователя и роль через пробел:\n"
        "<user_id> <role>\n\n"
        "Роли: admin (обычный админ), assistant (помощник)\n"
        "Пример: 123456789 admin\n\n"
        "Для отмены введите /cancel"
    )
    
    return ADDING_ADMIN

async def add_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == '/cancel':
        await update.message.reply_text("❌ Добавление админа отменено.")
        return ConversationHandler.END
    
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Неверный формат!\n\n"
            "Используйте: <user_id> <role>\n"
            "Пример: 123456789 admin"
        )
        return ADDING_ADMIN
    
    try:
        new_admin_id = int(parts[0])
        role = parts[1]
        
        if role not in ['admin', 'assistant']:
            await update.message.reply_text("❌ Неверная роль! Используйте: admin или assistant")
            return ADDING_ADMIN
        
        try:
            user = await context.bot.get_chat(new_admin_id)
            username = user.username or user.first_name or "unknown"
        except Exception as e:
            logger.error(f"Ошибка получения информации о пользователе {new_admin_id}: {e}")
            username = "unknown"
        
        add_admin(new_admin_id, username, role)
        
        await update.message.reply_text(f"✅ Админ @{username} (ID: {new_admin_id}) добавлен с ролью '{role}'")
        
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом!")
        return ADDING_ADMIN
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        return ADDING_ADMIN
    
    return ConversationHandler.END

async def remove_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_super_admin(user_id):
        await query.edit_message_text("❌ Только супер-админ может удалять админов.")
        return
    
    admins = get_admins()
    regular_admins = [admin for admin in admins if admin[2] != 'super_admin']
    
    if not regular_admins:
        await query.edit_message_text("❌ Нет обычных админов для удаления.")
        return
    
    keyboard = []
    for admin_id, admin_username, role in regular_admins:
        role_text = "🔵 Админ" if role == 'admin' else "🟢 Помощник"
        button_text = f"{role_text}: @{admin_username}"
        if len(button_text) > 30:
            button_text = button_text[:27] + "..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"remove_admin_{admin_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_manage_admins")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "➖ Выберите админа для удаления:",
        reply_markup=reply_markup
    )

async def execute_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not is_super_admin(user_id):
        await query.edit_message_text("❌ Только супер-админ может удалять админов.")
        return
    
    admin_id = int(query.data.replace("remove_admin_", ""))
    
    remove_admin(admin_id)
    
    await query.edit_message_text(f"✅ Админ (ID: {admin_id}) удален!")

async def handle_admin_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return
    
    if not is_admin(update.effective_user.id):
        return
    
    if update.message and update.message.text:
        text = update.message.text
        if text == '/admin':
            await admin_panel_group(update, context)

# ========== ГЛАВНАЯ ФУНКЦИЯ ==========

def main():
    global BOT_START_TIME
    BOT_START_TIME = datetime.now()
    
    init_db()
    
    application = Application.builder() \
        .token(BOT_TOKEN) \
        .read_timeout(30) \
        .write_timeout(30) \
        .connect_timeout(30) \
        .pool_timeout(30) \
        .build()
    
    # ========== CONVERSATION HANDLERS ==========
    
    # ConversationHandler для создания персонажа
    creation_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_character_start, pattern='^create_character$')],
        states={
            CREATING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_character_name)
            ],
            CREATING_AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_character_age)
            ],
            CREATING_BACKSTORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_character_backstory),
                CallbackQueryHandler(process_race_selection, pattern='^race_'),
                CallbackQueryHandler(process_class_selection, pattern='^class_')

CallbackQueryHandler(process_subrace_selection, pattern='^subrace_'),
            ],
            CREATING_APPEARANCE: [
                MessageHandler(filters.TEXT | filters.PHOTO, create_character_appearance)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_creation),
            CallbackQueryHandler(cancel_creation, pattern='^main_menu$')
        ],
        allow_reentry=True
    )
    
    # ConversationHandler для написания постов
    post_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_post_for_character, pattern='^post_char_'),
            CallbackQueryHandler(start_post_for_both_characters, pattern='^post_both_')
        ],
        states={
            WRITING_POST_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, post_code_handler),
                CommandHandler("cancel_post", cancel_post)
            ],
            WRITING_POST_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, post_content_handler),
                CommandHandler("end_post", end_post),
                CommandHandler("cancel_post", cancel_post)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_post),
            CallbackQueryHandler(cancel_post, pattern='^main_menu$')
        ],
        allow_reentry=True
    )
    
    # ConversationHandler для постов от системы
    system_post_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_system_post_start, pattern='^admin_system_post$')],
        states={
            WRITING_SYSTEM_POST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, system_post_handler),
                CommandHandler("end_system_post", end_system_post),
                CommandHandler("cancel_system_post", cancel_system_post)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_system_post),
            CallbackQueryHandler(cancel_system_post, pattern='^admin_back_to_panel$')
        ],
        allow_reentry=True
    )
    
    # ConversationHandler для постов от помощника
    assistant_post_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_assistant_post_start, pattern='^admin_assistant_post$')],
        states={
            WRITING_ASSISTANT_POST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, assistant_post_handler),
                CommandHandler("end_assistant_post", end_assistant_post),
                CommandHandler("cancel_assistant_post", cancel_assistant_post)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_assistant_post),
            CallbackQueryHandler(cancel_assistant_post, pattern='^admin_back_to_panel$')
        ],
        allow_reentry=True
    )
    
    # ConversationHandler для редактирования параметров
    edit_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_edit_parameter, pattern='^edit_(level|health|mana|strength|speed|agility|control|skill_points|hc_coins|fire|water|air|earth|group)_')
        ],
        states={
            EDITING_PARAM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_param_handler)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda update, context: ConversationHandler.END),
            CallbackQueryHandler(lambda update, context: ConversationHandler.END, pattern='^admin_back_to_panel$')
        ],
        allow_reentry=True
    )
    
    # ConversationHandler для причины отказа
    reject_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(reject_character_start, pattern='^reject_')],
        states={
            REJECTING_CHAR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reject_character_handler)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda update, context: ConversationHandler.END)
        ],
        allow_reentry=True
    )
    
    # ConversationHandler для добавления админа
    add_admin_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_admin_start, pattern='^add_admin_menu$')],
        states={
            ADDING_ADMIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_handler)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda update, context: ConversationHandler.END)
        ],
        allow_reentry=True
    )
    # ConversationHandler для добавления предметов
    add_item_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(item_select_character, pattern='^itemchar_')],
        states={
            ADDING_ITEM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_item_handler)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda update, context: ConversationHandler.END)
        ],
        allow_reentry=True
    )
    
    # ConversationHandler для редактирования предметов
    edit_item_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_item_selected, pattern='^edititem_')],
        states={
            EDITING_ITEM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_item_handler)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda update, context: ConversationHandler.END)
        ],
        allow_reentry=True
    )
    
    # ConversationHandler для добавления навыков
    add_skill_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(skill_select_character, pattern='^skillchar_')],
        states={
            ADDING_SKILL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_skill_handler)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda update, context: ConversationHandler.END)
        ],
        allow_reentry=True
    )
    
    # ConversationHandler для редактирования навыков
    edit_skill_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_skill_selected, pattern='^editskill_')],
        states={
            EDITING_SKILL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_skill_handler)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda update, context: ConversationHandler.END)
        ],
        allow_reentry=True
    )
    
    
    # ========== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ==========
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("helpnng", help_nng))
    application.add_handler(CommandHandler("uptime", bot_uptime))
    application.add_handler(CommandHandler("stop_uptime", stop_uptime))
    application.add_handler(CommandHandler("maintenance", maintenance_notice))
    application.add_handler(CommandHandler("set_posts_here", setup_posts_chat))
    application.add_handler(CommandHandler("set_characters_here", setup_characters_chat))
    application.add_handler(CommandHandler("set_status_here", setup_status_chat))
    application.add_handler(CommandHandler("settings", show_settings))
    application.add_handler(CommandHandler("give_points", admin_give_points))
    application.add_handler(CommandHandler("give_exp", admin_give_exp))
    application.add_handler(CommandHandler("admin", admin_panel_group))
    application.add_handler(CommandHandler("auto_uptime", auto_uptime))
    
    # Conversation handlers (должны быть ДО обработчика кнопок)
    application.add_handler(creation_conv_handler)
    application.add_handler(post_conv_handler)
    application.add_handler(system_post_conv_handler)
    application.add_handler(assistant_post_conv_handler)
    application.add_handler(edit_conv_handler)
    application.add_handler(reject_conv_handler)
    application.add_handler(add_admin_conv_handler)

application.add_handler(add_item_conv_handler)
    application.add_handler(edit_item_conv_handler)
    application.add_handler(add_skill_conv_handler)
    application.add_handler(edit_skill_conv_handler)
    
    # Callback handler (должен быть ПОСЛЕ ConversationHandler)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик сообщений в админской группе
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(ADMIN_CHAT_ID),
        handle_admin_group_message
    ))
    
    # Обработчик ошибок
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Ошибка: {context.error}")
    
    application.add_error_handler(error_handler)
    
    print("🤖 Бот NoNameGame запускается...")
    print(f"⏰ Время запуска: {BOT_START_TIME.strftime('%d.%m.%Y %H:%M:%S')}")
    print("✅ Бот успешно запущен!")
    
    application.run_polling()

if __name__ == '__main__':
    main()
