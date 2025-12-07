"""
Модуль для работы с SQLite базой данных
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Tuple, Dict


DB_FILE = "bot_database.db"


def get_db_connection():
    """Создает и возвращает соединение с базой данных"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Инициализирует базу данных и создает все необходимые таблицы"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            username TEXT,
            first_start TEXT NOT NULL
        )
    """)
    
    # Таблица администраторов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            username TEXT,
            added_date TEXT NOT NULL
        )
    """)
    
    # Таблица черного списка
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            username TEXT,
            banned_date TEXT NOT NULL,
            banned_by TEXT
        )
    """)
    
    # Таблица достижений
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            ach_id TEXT PRIMARY KEY,
            ach_name TEXT NOT NULL,
            created TEXT NOT NULL
        )
    """)
    
    # Таблица достижений пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ach_id TEXT NOT NULL,
            given_date TEXT NOT NULL,
            given_by TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (ach_id) REFERENCES achievements(ach_id)
        )
    """)
    
    # Таблица балансов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Таблица временных банов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_bans (
            user_id INTEGER PRIMARY KEY,
            unban_time TEXT NOT NULL,
            reason TEXT NOT NULL,
            banned_by INTEGER NOT NULL,
            banned_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Таблица логов пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            username TEXT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL
        )
    """)
    
    # Таблица логов администраторов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            username TEXT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL
        )
    """)
    
    # Таблица логов команд администраторов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_command_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            username TEXT,
            timestamp TEXT NOT NULL,
            command TEXT NOT NULL
        )
    """)
    
    # Таблица системных логов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            initiator TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL
        )
    """)
    
    # Таблица логов ошибок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            error_message TEXT NOT NULL,
            context TEXT
        )
    """)
    
    # Таблица логов переводов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfer_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            from_user_id INTEGER NOT NULL,
            to_user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            from_name TEXT NOT NULL,
            to_name TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()


# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ==========

def add_user(user_id: int, full_name: str, username: str, first_start: str):
    """Добавляет пользователя в базу данных"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, full_name, username, first_start)
        VALUES (?, ?, ?, ?)
    """, (user_id, full_name, username, first_start))
    conn.commit()
    conn.close()


def get_user_profile(user_id: int) -> Optional[dict]:
    """Получает профиль пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": str(row["user_id"]),
            "name": row["full_name"],
            "username": row["username"] or "NA",
            "first_start": row["first_start"]
        }
    return None


def get_all_users() -> List[str]:
    """Получает список всех ID пользователей"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [str(row["user_id"]) for row in rows]


def get_user_by_id_or_username(identifier: str) -> Optional[Tuple[str, str, str]]:
    """Находит пользователя по ID или username"""
    identifier = identifier.lstrip("@")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if identifier.isdigit():
        cursor.execute("SELECT user_id, full_name, username FROM users WHERE user_id = ?", (int(identifier),))
    else:
        cursor.execute("SELECT user_id, full_name, username FROM users WHERE username = ?", (identifier,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return (str(row["user_id"]), row["full_name"], row["username"] or "NA")
    return None


# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С АДМИНИСТРАТОРАМИ ==========

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM admins WHERE admin_id = ?", (user_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result


def add_admin(admin_id: int, full_name: str, username: str, added_date: str):
    """Добавляет администратора"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO admins (admin_id, full_name, username, added_date)
        VALUES (?, ?, ?, ?)
    """, (admin_id, full_name, username, added_date))
    conn.commit()
    conn.close()


def remove_admin(admin_id: int) -> bool:
    """Удаляет администратора"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE admin_id = ?", (admin_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_all_admins() -> List[dict]:
    """Получает список всех администраторов"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": str(row["admin_id"]),
            "name": row["full_name"],
            "username": row["username"] or "NA",
            "added_date": row["added_date"]
        }
        for row in rows
    ]


# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ЧЕРНЫМ СПИСКОМ ==========

def is_banned(user_id: int) -> bool:
    """Проверяет, заблокирован ли пользователь"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM blacklist WHERE user_id = ?", (user_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result


def ban_user(user_id: int, full_name: str, username: str, banned_date: str, banned_by: str):
    """Добавляет пользователя в черный список"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO blacklist (user_id, full_name, username, banned_date, banned_by)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, full_name, username, banned_date, banned_by))
    conn.commit()
    conn.close()


def unban_user(user_id: int) -> bool:
    """Удаляет пользователя из черного списка"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_all_banned_users() -> List[dict]:
    """Получает список всех забаненных пользователей"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blacklist")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": str(row["user_id"]),
            "name": row["full_name"],
            "username": row["username"] or "NA",
            "banned_date": row["banned_date"],
            "banned_by": row["banned_by"] or "NA"
        }
        for row in rows
    ]


# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С БАЛАНСОМ ==========

def get_user_balance(user_id: int) -> int:
    """Получает баланс пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM balances WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["balance"] if row else 0


def set_user_balance(user_id: int, amount: int):
    """Устанавливает баланс пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO balances (user_id, balance)
        VALUES (?, ?)
    """, (user_id, amount))
    conn.commit()
    conn.close()


def add_user_balance(user_id: int, amount: int):
    """Добавляет баланс пользователю"""
    current = get_user_balance(user_id)
    set_user_balance(user_id, current + amount)


def remove_user_balance(user_id: int, amount: int) -> int:
    """Снимает баланс у пользователя"""
    current = get_user_balance(user_id)
    new_balance = max(0, current - amount)
    set_user_balance(user_id, new_balance)
    return new_balance


def get_top_users_by_balance(limit: int = 10) -> List[Tuple[int, int]]:
    """Получает топ пользователей по балансу"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, balance FROM balances
        WHERE balance > 0
        ORDER BY balance DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [(row["user_id"], row["balance"]) for row in rows]


# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ДОСТИЖЕНИЯМИ ==========

def create_achievement(ach_id: str, ach_name: str, created: str):
    """Создает новое достижение"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO achievements (ach_id, ach_name, created)
        VALUES (?, ?, ?)
    """, (ach_id, ach_name, created))
    conn.commit()
    conn.close()


def delete_achievement(ach_id: str) -> bool:
    """Удаляет достижение из системы"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM achievements WHERE ach_id = ?", (ach_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_all_achievements() -> List[dict]:
    """Получает список всех достижений"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM achievements")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row["ach_id"],
            "name": row["ach_name"],
            "created": row["created"]
        }
        for row in rows
    ]


def add_user_achievement(user_id: int, ach_id: str, given_date: str, given_by: str):
    """Добавляет достижение пользователю"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_achievements (user_id, ach_id, given_date, given_by)
        VALUES (?, ?, ?, ?)
    """, (user_id, ach_id, given_date, given_by))
    conn.commit()
    conn.close()


def get_user_achievements(user_id: int) -> List[dict]:
    """Получает список достижений пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ua.ach_id, ua.given_date, ua.given_by, a.ach_name
        FROM user_achievements ua
        JOIN achievements a ON ua.ach_id = a.ach_id
        WHERE ua.user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row["ach_id"],
            "name": row["ach_name"],
            "date": row["given_date"],
            "given_by": row["given_by"]
        }
        for row in rows
    ]


def remove_achievement_from_user(user_id: int, ach_id: str) -> bool:
    """Удаляет достижение у пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM user_achievements
        WHERE user_id = ? AND ach_id = ?
    """, (user_id, ach_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ВРЕМЕННЫМИ БАНАМИ ==========

def add_temp_ban(user_id: int, unban_time: str, reason: str, banned_by: int, banned_at: str):
    """Добавляет временный бан"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO temp_bans (user_id, unban_time, reason, banned_by, banned_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, unban_time, reason, banned_by, banned_at))
    conn.commit()
    conn.close()


def get_temp_bans() -> List[dict]:
    """Получает список временных банов"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM temp_bans")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "user_id": str(row["user_id"]),
            "unban_time": row["unban_time"],
            "reason": row["reason"],
            "banned_by": str(row["banned_by"]),
            "banned_at": row["banned_at"]
        }
        for row in rows
    ]


def is_temp_banned(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя активный временный бан"""
    temp_bans = get_temp_bans()
    now = datetime.now()
    
    for ban in temp_bans:
        if ban["user_id"] == str(user_id):
            try:
                unban_time = datetime.strptime(ban["unban_time"], "%Y-%m-%d %H:%M:%S")
                if unban_time > now:
                    return True
            except ValueError:
                continue
    return False


def remove_expired_temp_bans() -> List[int]:
    """Удаляет истекшие временные баны и возвращает список разбаненных пользователей"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Получаем истекшие баны
    cursor.execute("SELECT user_id FROM temp_bans WHERE unban_time <= ?", (now,))
    expired_rows = cursor.fetchall()
    expired_user_ids = [row["user_id"] for row in expired_rows]
    
    # Удаляем истекшие баны
    cursor.execute("DELETE FROM temp_bans WHERE unban_time <= ?", (now,))
    conn.commit()
    conn.close()
    
    return expired_user_ids


def remove_temp_ban(user_id: int) -> bool:
    """Удаляет временный бан пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM temp_bans WHERE user_id = ?", (user_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ========== ФУНКЦИИ ДЛЯ ЛОГИРОВАНИЯ ==========

def log_user_action(user_id: int, full_name: str, username: str, timestamp: str, action: str):
    """Логирует действие пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_logs (user_id, full_name, username, timestamp, action)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, full_name, username or "NA", timestamp, action))
    conn.commit()
    conn.close()


def log_admin_action(user_id: int, full_name: str, username: str, timestamp: str, action: str):
    """Логирует действие администратора"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO admin_logs (user_id, full_name, username, timestamp, action)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, full_name, username or "NA", timestamp, action))
    conn.commit()
    conn.close()


def log_admin_command(user_id: int, full_name: str, username: str, timestamp: str, command: str):
    """Логирует команду администратора"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO admin_command_logs (user_id, full_name, username, timestamp, command)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, full_name, username or "NA", timestamp, command))
    conn.commit()
    conn.close()


def log_system_event(initiator: str, timestamp: str, action: str):
    """Логирует системное событие"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO system_logs (initiator, timestamp, action)
        VALUES (?, ?, ?)
    """, (initiator, timestamp, action))
    conn.commit()
    conn.close()


def log_error(error_type: str, timestamp: str, error_message: str, context: str = ""):
    """Логирует ошибку"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO error_logs (error_type, timestamp, error_message, context)
        VALUES (?, ?, ?, ?)
    """, (error_type, timestamp, error_message, context or ""))
    conn.commit()
    conn.close()


def log_transfer(timestamp: str, from_user_id: int, to_user_id: int, amount: int, from_name: str, to_name: str):
    """Логирует перевод TPCoin"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transfer_logs (timestamp, from_user_id, to_user_id, amount, from_name, to_name)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, from_user_id, to_user_id, amount, from_name, to_name))
    conn.commit()
    conn.close()


def get_last_logs(table_name: str, count: int = 20) -> List[str]:
    """Получает последние N записей из таблицы логов"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if table_name == "user_logs":
        cursor.execute("""
            SELECT user_id, full_name, username, timestamp, action
            FROM user_logs
            ORDER BY id DESC
            LIMIT ?
        """, (count,))
        rows = cursor.fetchall()
        logs = [
            f"{row['user_id']} | {row['full_name']} | {row['username']} | {row['timestamp']} | {row['action']}\n"
            for row in reversed(rows)
        ]
    elif table_name == "admin_logs":
        cursor.execute("""
            SELECT user_id, full_name, username, timestamp, action
            FROM admin_logs
            ORDER BY id DESC
            LIMIT ?
        """, (count,))
        rows = cursor.fetchall()
        logs = [
            f"{row['user_id']} | {row['full_name']} | {row['username']} | {row['timestamp']} | {row['action']}\n"
            for row in reversed(rows)
        ]
    elif table_name == "admin_command_logs":
        cursor.execute("""
            SELECT user_id, full_name, username, timestamp, command
            FROM admin_command_logs
            ORDER BY id DESC
            LIMIT ?
        """, (count,))
        rows = cursor.fetchall()
        logs = [
            f"{row['user_id']} | {row['full_name']} | {row['username']} | {row['timestamp']} | {row['command']}\n"
            for row in reversed(rows)
        ]
    elif table_name == "system_logs":
        cursor.execute("""
            SELECT initiator, timestamp, action
            FROM system_logs
            ORDER BY id DESC
            LIMIT ?
        """, (count,))
        rows = cursor.fetchall()
        logs = [
            f"{row['initiator']} | {row['timestamp']} | {row['action']}\n"
            for row in reversed(rows)
        ]
    elif table_name == "error_logs":
        cursor.execute("""
            SELECT error_type, timestamp, error_message, context
            FROM error_logs
            ORDER BY id DESC
            LIMIT ?
        """, (count,))
        rows = cursor.fetchall()
        logs = [
            f"{row['error_type']} | {row['timestamp']} | {row['error_message']}{' | ' + row['context'] if row['context'] else ''}\n"
            for row in reversed(rows)
        ]
    else:
        logs = []
    
    conn.close()
    return logs


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_total_users_count() -> int:
    """Получает общее количество пользователей"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users")
    count = cursor.fetchone()["count"]
    conn.close()
    return count


def get_new_users_last_24h() -> int:
    """Получает количество новых пользователей за последние 24 часа"""
    from datetime import timedelta
    now = datetime.now()
    day_ago = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE first_start >= ?", (day_ago,))
    count = cursor.fetchone()["count"]
    conn.close()
    return count


def get_admins_count() -> int:
    """Получает количество администраторов"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM admins")
    count = cursor.fetchone()["count"]
    conn.close()
    return count


def get_achievements_count() -> int:
    """Получает общее количество достижений"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM achievements")
    count = cursor.fetchone()["count"]
    conn.close()
    return count


def get_logs_statistics() -> dict:
    """Получает статистику по таблицам логов"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Подсчитываем записи в каждой таблице логов
    log_tables = [
        "user_logs",
        "admin_logs",
        "admin_command_logs",
        "system_logs",
        "error_logs",
        "transfer_logs"
    ]
    
    for table in log_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()["count"]
            stats[table] = count
        except Exception:
            stats[table] = 0
    
    # Получаем размер базы данных
    try:
        db_size = os.path.getsize(DB_FILE) if os.path.exists(DB_FILE) else 0
        stats["db_size"] = db_size
    except Exception:
        stats["db_size"] = 0
    
    conn.close()
    return stats
