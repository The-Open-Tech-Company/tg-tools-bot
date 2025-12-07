"""
Telegram бот на aiogram 3
Объединенный файл со всем функционалом
Использует SQLite базу данных вместо файлов .txt
"""
import os
import json
import asyncio
import time
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Импорт TON Connect
from tonutils.tonconnect import TonConnect
from tonutils.tonconnect.utils.exceptions import TonConnectError, UserRejectsError
from tonconnect_storage import FileStorage

# Импорт функций для работы с базой данных
from database import (
    init_database,
    add_user,
    get_user_profile,
    get_all_users,
    get_user_by_id_or_username,
    is_admin,
    add_admin,
    remove_admin,
    get_all_admins,
    is_banned,
    ban_user as db_ban_user,
    unban_user as db_unban_user,
    get_all_banned_users,
    get_user_balance,
    set_user_balance,
    add_user_balance,
    remove_user_balance,
    get_top_users_by_balance,
    create_achievement,
    delete_achievement,
    get_all_achievements,
    add_user_achievement,
    get_user_achievements,
    remove_achievement_from_user,
    add_temp_ban,
    get_temp_bans,
    is_temp_banned,
    remove_expired_temp_bans,
    remove_temp_ban,
    log_user_action as db_log_user_action,
    log_admin_action as db_log_admin_action,
    log_admin_command as db_log_admin_command,
    log_system_event as db_log_system_event,
    log_error as db_log_error,
    log_transfer as db_log_transfer,
    get_last_logs,
    get_total_users_count,
    get_new_users_last_24h,
    get_admins_count,
    get_achievements_count,
    get_logs_statistics
)

# ========== КОНФИГУРАЦИЯ ==========
# Загрузка конфигурации из config.json
CONFIG_FILE = "config.json"

def load_config():
    """Загружает конфигурацию из config.json"""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Файл конфигурации {CONFIG_FILE} не найден! Создайте файл с BOT_TOKEN и CREATOR_ID.")
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        if "BOT_TOKEN" not in config:
            raise ValueError("BOT_TOKEN не найден в config.json!")
        if "CREATOR_ID" not in config:
            raise ValueError("CREATOR_ID не найден в config.json!")
        
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка парсинга config.json: {e}")

config = load_config()
BOT_TOKEN = config["BOT_TOKEN"]
CREATOR_ID = config["CREATOR_ID"]

# ========== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ==========
# Инициализируем базу данных при запуске
init_database()

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
if not BOT_TOKEN or BOT_TOKEN == "ваш_токен_бота":
    raise ValueError("BOT_TOKEN не установлен! Укажите токен бота в config.json")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== ИНИЦИАЛИЗАЦИЯ TON CONNECT ==========
# URL манифеста для TON Connect (нужно разместить на публичном URL)
TC_MANIFEST_URL = "https://raw.githubusercontent.com/The-Open-Tech-Company/tg-tools-bot/refs/heads/main/tonconnect-manifest.json"
TC_STORAGE = FileStorage("tonconnect_connections.json")

async def check_manifest_format(manifest_url: str) -> bool:
    """Проверяет формат манифеста на наличие угловых скобок"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(manifest_url) as response:
                if response.status == 200:
                    content = await response.text()
                    # Проверяем наличие угловых скобок вокруг значений
                    if '<' in content and '>' in content:
                        # Проверяем, не являются ли они частью URL или HTML тегов
                        import re
                        # Ищем паттерн типа "<https://...>" или "<text>"
                        if re.search(r'<https?://[^>]+>', content) or re.search(r'"[^"]*<[^>]+>[^"]*"', content):
                            print(f"⚠️ Обнаружены угловые скобки в манифесте!")
                            print(f"Содержимое манифеста:\n{content}")
                            return False
                    return True
                else:
                    print(f"⚠️ Не удалось загрузить манифест. HTTP статус: {response.status}")
                    return False
    except Exception as e:
        print(f"⚠️ Ошибка при проверке манифеста: {e}")
        return False

# Проверяем формат манифеста перед инициализацией
print(f"Проверка манифеста по URL: {TC_MANIFEST_URL}")
manifest_check = asyncio.run(check_manifest_format(TC_MANIFEST_URL))

# Флаг доступности TON Connect
TON_CONNECT_AVAILABLE = False
tc = None

# Инициализируем TON Connect с обработкой ошибок
try:
    tc = TonConnect(
        storage=TC_STORAGE,
        manifest_url=TC_MANIFEST_URL,
        wallets_fallback_file_path="./wallets.json"
    )
    TON_CONNECT_AVAILABLE = True
    print(f"✅ TON Connect инициализирован. Manifest URL: {TC_MANIFEST_URL}")
except Exception as e:
    error_msg = str(e)
    print(f"⚠️ TON Connect недоступен: {error_msg}")
    print(f"Проверьте доступность манифеста по URL: {TC_MANIFEST_URL}")
    
    # Проверяем, связана ли ошибка с манифестом
    if "manifest" in error_msg.lower() or "ManifestContentError" in error_msg or "ManifestNotFoundError" in error_msg:
        print("\n⚠️ Проблема с манифестом:")
        print("1. Убедитесь, что манифест доступен по указанному URL")
        print("2. Проверьте формат JSON манифеста (не должно быть угловых скобок вокруг значений)")
        print("3. Правильный формат:")
        print('   {"url": "https://...", "name": "...", ...}')
        print("4. Неправильный формат:")
        print('   {"url": "<https://...>", "name": "<...>", ...}')
        print("\nПопробуйте открыть манифест в браузере и проверить его содержимое")
        if not manifest_check:
            print("\n❌ Проверка манифеста показала наличие угловых скобок!")
            print("Исправьте манифест на сервере, удалив угловые скобки вокруг значений.")
    
    print("\n⚠️ Бот будет запущен без поддержки TON Connect.")
    print("Команды /tonconnect и /tonconnect_disconnect будут недоступны.")

# Словарь для хранения активных подключений кошельков
# Формат: {user_id: connector}
active_connectors: Dict[int, any] = {}

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ФАЙЛАМИ ==========

def get_user_info(user) -> Tuple[str, str, str]:
    """Получает информацию о пользователе в формате (id, имя, username)"""
    user_id = str(user.id)
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "NA"
    username = user.username or "NA"
    return user_id, full_name, username


def log_error(error_type: str, error_message: str, context: str = ""):
    """Логирует ошибку бота"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        db_log_error(error_type, timestamp, error_message, context)
    except Exception as e:
        # Если не удалось записать в лог ошибок, пытаемся записать в системный лог
        try:
            db_log_system_event("SYSTEM", timestamp, f"Ошибка записи в errorlogs: {str(e)}")
        except:
            pass


def log_user_action(user, action: str):
    """Логирует действие обычного пользователя"""
    try:
        user_id, full_name, username = get_user_info(user)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db_log_user_action(int(user_id), full_name, username, timestamp, action)
    except Exception as e:
        log_error("LOG_USER_ACTION", f"Ошибка логирования действия пользователя", str(e))


def log_admin_action(user, action: str):
    """Логирует действие администратора"""
    try:
        user_id, full_name, username = get_user_info(user)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db_log_admin_action(int(user_id), full_name, username, timestamp, action)
    except Exception as e:
        log_error("LOG_ADMIN_ACTION", f"Ошибка логирования действия администратора", str(e))


def log_admin_command(user, command: str):
    """Логирует команду администратора"""
    try:
        user_id, full_name, username = get_user_info(user)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db_log_admin_command(int(user_id), full_name, username, timestamp, command)
    except Exception as e:
        log_error("LOG_ADMIN_COMMAND", f"Ошибка логирования команды администратора", str(e))


def log_system_event(initiator: str, action: str):
    """Логирует системное событие"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db_log_system_event(initiator, timestamp, action)
    except Exception as e:
        # Если не удалось записать системный лог, пытаемся записать в лог ошибок
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db_log_error("SYSTEM_LOG_ERROR", timestamp, f"Ошибка записи системного лога: {str(e)}", "")
        except:
            pass


def add_user_to_list(user):
    """Добавляет пользователя в список пользователей, если его там еще нет"""
    user_id, full_name, username = get_user_info(user)
    
    # Проверяем, есть ли пользователь уже в списке
    profile = get_user_profile(int(user_id))
    if profile:
        return  # Пользователь уже в списке
    
    # Добавляем нового пользователя
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_user(int(user_id), full_name, username, timestamp)


# Функция is_admin уже импортирована из database

def add_admin(user, admin_user):
    """Добавляет администратора в список"""
    admin_id, full_name, username = get_user_info(admin_user)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    from database import add_admin as db_add_admin
    db_add_admin(int(admin_id), full_name, username, timestamp)
    log_admin_command(user, f"addadmin {admin_id}")


def remove_admin(user, admin_id: str):
    """Удаляет администратора из списка"""
    from database import remove_admin as db_remove_admin
    removed = db_remove_admin(int(admin_id))
    if removed:
        log_admin_command(user, f"unadmin {admin_id}")
    return removed


# Функция is_banned уже импортирована из database

def ban_user(user, target_user):
    """Добавляет пользователя в черный список"""
    target_id, full_name, username = get_user_info(target_user)
    admin_id, admin_name, admin_username = get_user_info(user)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    banned_by = f"{admin_id} {admin_username}"
    db_ban_user(int(target_id), full_name, username, timestamp, banned_by)
    log_admin_command(user, f"ban {target_id}")


def unban_user(user, target_id: str):
    """Удаляет пользователя из черного списка"""
    removed = db_unban_user(int(target_id))
    if removed:
        log_admin_command(user, f"unban {target_id}")
    return removed


# Функции get_user_by_id_or_username и get_user_profile уже импортированы из database


# Функции работы с балансом уже импортированы из database


# Функции работы с достижениями уже импортированы из database

def add_achievement(user, target_user, ach_id: str, ach_name: str):
    """Добавляет достижение пользователю"""
    target_id, full_name, username = get_user_info(target_user)
    admin_id, admin_name, admin_username = get_user_info(user)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    given_by = f"{admin_id} {admin_username}"
    add_user_achievement(int(target_id), ach_id, timestamp, given_by)
    log_admin_command(user, f"sendach {ach_id} {target_id}")


def create_achievement(user, ach_id: str, ach_name: str):
    """Создает новое достижение"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    from database import create_achievement as db_create_achievement
    db_create_achievement(ach_id, ach_name, timestamp)
    log_admin_command(user, f"newach {ach_id} {ach_name}")


def remove_achievement_from_user(user, target_user_id: str, ach_id: str) -> bool:
    """Удаляет достижение у пользователя"""
    from database import remove_achievement_from_user as db_remove_achievement_from_user
    removed = db_remove_achievement_from_user(int(target_user_id), ach_id)
    if removed:
        log_admin_command(user, f"removeach {ach_id} {target_user_id}")
    return removed


def delete_achievement(user, ach_id: str) -> bool:
    """Удаляет достижение из системы"""
    from database import delete_achievement as db_delete_achievement
    removed = db_delete_achievement(ach_id)
    if removed:
        log_admin_command(user, f"deleteach {ach_id}")
    return removed


# Функции работы с временными банами уже импортированы из database

def add_temp_ban(user_id: int, duration_hours: int, reason: str, banned_by: int):
    """Добавляет временный бан"""
    unban_time = datetime.now() + timedelta(hours=duration_hours)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    unban_timestamp = unban_time.strftime("%Y-%m-%d %H:%M:%S")
    add_temp_ban(user_id, unban_timestamp, reason, banned_by, timestamp)
    return unban_time


# Все эти функции уже импортированы из database


def get_all_admin_ids() -> List[int]:
    """Получает список всех ID администраторов (включая создателя)"""
    admin_ids = [CREATOR_ID]
    admins = get_all_admins()
    for admin in admins:
        admin_ids.append(int(admin["id"]))
    return admin_ids


def log_transfer(from_user_id: int, to_user_id: int, amount: int, from_name: str, to_name: str):
    """Логирует перевод TPCoin между пользователями"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db_log_transfer(timestamp, from_user_id, to_user_id, amount, from_name, to_name)
    except Exception as e:
        log_error("LOG_TRANSFER", f"Ошибка логирования перевода", str(e))


def check_log_files() -> dict:
    """Проверяет доступность таблиц логов в базе данных"""
    # Для SQLite всегда возвращаем True, так как таблицы создаются автоматически
    result = {
        "userlogs.txt": {"exists": True, "size": 0},
        "adminlogs.txt": {"exists": True, "size": 0},
        "admin-com-logs.txt": {"exists": True, "size": 0},
        "systemlogs.txt": {"exists": True, "size": 0},
        "errorlogs.txt": {"exists": True, "size": 0},
        "transferlogs.txt": {"exists": True, "size": 0}
    }
    return result


# ========== FSM СОСТОЯНИЯ ДЛЯ СИСТЕМЫ ПОДДЕРЖКИ ==========

class SupportStates(StatesGroup):
    waiting_for_message = State()  # Пользователь пишет сообщение в поддержку
    waiting_for_addition = State()  # Пользователь пишет дополнение
    admin_waiting_for_reply = State()  # Админ пишет ответ пользователю
    admin_waiting_for_reply_to_addition = State()  # Админ отвечает на дополнение

# Словарь для хранения активных диалогов поддержки
# Формат: {user_id: {"admin_id": admin_id, "message_id": message_id}}
active_support_dialogs: Dict[int, Dict] = {}

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_user_status(user_id: int) -> str:
    """Определяет статус пользователя"""
    if user_id == CREATOR_ID:
        return "Creator"
    elif is_admin(user_id):
        return "Admin"
    else:
        return "User"


async def get_user_by_id_or_username_async(identifier: str) -> Optional[Tuple[str, str, str]]:
    """Находит пользователя по ID или username, сначала в файле, потом через API"""
    # Убираем @ если есть
    identifier = identifier.lstrip("@")
    
    # Сначала ищем в файле
    user_info = get_user_by_id_or_username(identifier)
    if user_info:
        return user_info
    
    # Если не найден в файле, пробуем получить через API (если это числовой ID)
    if identifier.isdigit():
        try:
            chat = await bot.get_chat(int(identifier))
            if chat.type == "private":
                user_id = str(chat.id)
                full_name = f"{chat.first_name or ''} {chat.last_name or ''}".strip() or "NA"
                username = chat.username or "NA"
                return (user_id, full_name, username)
        except Exception:
            pass
    
    return None


async def check_ban_middleware(message: Message):
    """Проверяет, заблокирован ли пользователь"""
    if is_banned(message.from_user.id):
        await message.answer("Вы заблокированы администратором. Доступ ограничен")
        return False
    return True


# ========== ОБЩИЕ КОМАНДЫ ==========

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    try:
        if not await check_ban_middleware(message):
            return
        
        add_user_to_list(message.from_user)
        log_user_action(message.from_user, "/start")
        
        welcome_text = (
            "👋 Добро пожаловать в бота!\n\n"
            "Используйте /profile для просмотра профиля\n"
            "Используйте /balance для просмотра баланса\n"
            "Используйте /myach для просмотра достижений"
        )
        await message.answer(welcome_text)
    except Exception as e:
        log_error("CMD_START", str(e), f"User ID: {message.from_user.id}")
        await message.answer("❌ Произошла ошибка при выполнении команды. Попробуйте позже.")


@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    """Команда /profile"""
    if not await check_ban_middleware(message):
        return
    
    log_user_action(message.from_user, "/profile")
    
    profile = get_user_profile(message.from_user.id)
    if not profile:
        await message.answer("Профиль не найден. Используйте /start для регистрации.")
        return
    
    status = get_user_status(message.from_user.id)
    
    profile_text = (
        f"👤 Профиль пользователя\n\n"
        f"Имя и Фамилия: {profile['name']}\n"
        f"Telegram ID: {profile['id']}\n"
        f"Статус: {status}\n"
        f"Дата первого запуска: {profile['first_start']}"
    )
    await message.answer(profile_text)


@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    """Команда /balance"""
    if not await check_ban_middleware(message):
        return
    
    log_user_action(message.from_user, "/balance")
    
    balance = get_user_balance(message.from_user.id)
    await message.answer(f"💰 Ваш баланс: {balance} TPCoin")


@dp.message(Command("myach"))
async def cmd_myach(message: Message):
    """Команда /myach"""
    if not await check_ban_middleware(message):
        return
    
    log_user_action(message.from_user, "/myach")
    
    achievements = get_user_achievements(message.from_user.id)
    
    if not achievements:
        await message.answer("У вас пока нет достижений.")
        return
    
    ach_text = "🏆 Ваши достижения:\n\n"
    for ach in achievements:
        ach_text += f"• {ach['name']} (ID: {ach['id']})\n"
        ach_text += f"  Получено: {ach['date']}\n\n"
    
    await message.answer(ach_text)


@dp.message(Command("transfer"))
async def cmd_transfer(message: Message):
    """Команда /transfer - перевод TPCoin между пользователями"""
    if not await check_ban_middleware(message):
        return
    
    log_user_action(message.from_user, "/transfer")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if len(args) < 2:
        await message.answer("Использование: /transfer количество id_получателя или /transfer количество @username")
        return
    
    try:
        amount = int(args[0])
        if amount <= 0:
            await message.answer("❌ Сумма перевода должна быть положительным числом.")
            return
    except ValueError:
        await message.answer("❌ Сумма перевода должна быть числом.")
        return
    
    # Проверяем достаточность баланса
    sender_id = message.from_user.id
    sender_balance = get_user_balance(sender_id)
    
    if sender_balance < amount:
        await message.answer(f"❌ Недостаточно средств. Ваш баланс: {sender_balance} TPCoin")
        return
    
    # Получаем информацию о получателе
    recipient_identifier = args[1]
    recipient_info = await get_user_by_id_or_username_async(recipient_identifier)
    
    if not recipient_info:
        await message.answer(f"❌ Пользователь {recipient_identifier} не найден.")
        return
    
    recipient_id = int(recipient_info[0])
    
    # Проверяем, что пользователь не переводит самому себе
    if recipient_id == sender_id:
        await message.answer("❌ Нельзя перевести средства самому себе.")
        return
    
    # Проверяем, что получатель не забанен (опционально, можно убрать если нужно)
    if is_banned(recipient_id):
        await message.answer("❌ Нельзя перевести средства забаненному пользователю.")
        return
    
    # Выполняем перевод
    try:
        # Списываем средства у отправителя
        set_user_balance(sender_id, sender_balance - amount)
        
        # Добавляем средства получателю
        recipient_balance = get_user_balance(recipient_id)
        set_user_balance(recipient_id, recipient_balance + amount)
        
        # Логируем перевод
        sender_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or "NA"
        recipient_name = recipient_info[1]
        log_transfer(sender_id, recipient_id, amount, sender_name, recipient_name)
        
        # Отправляем уведомление получателю
        try:
            await bot.send_message(
                chat_id=recipient_id,
                text=f"💰 Вы получили перевод от {sender_name} (@{message.from_user.username or 'отсутствует'})\n"
                     f"Сумма: {amount} TPCoin\n"
                     f"Ваш новый баланс: {recipient_balance + amount} TPCoin"
            )
        except Exception as e:
            log_error("TRANSFER_NOTIFICATION", f"Ошибка отправки уведомления получателю {recipient_id}", str(e))
        
        # Подтверждение отправителю
        await message.answer(
            f"✅ Перевод выполнен успешно!\n\n"
            f"Получатель: {recipient_name} (@{recipient_info[2] if recipient_info[2] != 'NA' else 'отсутствует'})\n"
            f"Сумма: {amount} TPCoin\n"
            f"Ваш новый баланс: {sender_balance - amount} TPCoin"
        )
        
        log_user_action(message.from_user, f"/transfer {amount} to {recipient_id}")
        
    except Exception as e:
        log_error("TRANSFER", f"Ошибка выполнения перевода от {sender_id} к {recipient_id}", str(e))
        await message.answer("❌ Произошла ошибка при выполнении перевода. Попробуйте позже.")


@dp.message(Command("contact"))
async def cmd_contact(message: Message, state: FSMContext):
    """Команда /contact - отправка сообщения в поддержку"""
    if not await check_ban_middleware(message):
        return
    
    # Проверяем, не является ли пользователь админом
    if is_admin(message.from_user.id) or message.from_user.id == CREATOR_ID:
        await message.answer("❌ Эта команда доступна только обычным пользователям.")
        return
    
    log_user_action(message.from_user, "/contact")
    
    # Проверяем, есть ли активный диалог
    if message.from_user.id in active_support_dialogs:
        await message.answer(
            "⚠️ У вас уже есть активный диалог с поддержкой.\n"
            "Дождитесь ответа администратора или завершения текущего диалога."
        )
        return
    
    await message.answer(
        "📝 Напишите ваше сообщение для администраторов бота.\n"
        "Опишите вашу проблему или вопрос, и мы постараемся помочь."
    )
    await state.set_state(SupportStates.waiting_for_message)


@dp.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext):
    """Обработка сообщения пользователя в поддержку"""
    if not await check_ban_middleware(message):
        await state.clear()
        return
    
    user_id = message.from_user.id
    user_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or "Без имени"
    username = f"@{message.from_user.username}" if message.from_user.username else "отсутствует"
    
    # Формируем текст сообщения для админов
    admin_message_text = (
        f"📨 Новое сообщение от пользователя\n\n"
        f"👤 Имя: {user_name}\n"
        f"📱 Username: {username}\n"
        f"🆔 ID: {user_id}\n\n"
        f"💬 Сообщение:\n{message.text or 'Медиа-сообщение'}"
    )
    
    # Создаем кнопку для админов
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Прочитать и ответить", callback_data=f"support_read_{user_id}")]
    ])
    
    # Отправляем сообщение всем админам
    admin_ids = get_all_admin_ids()
    sent_count = 0
    
    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_message_text,
                reply_markup=keyboard
            )
            sent_count += 1
        except Exception as e:
            log_error("SUPPORT_SEND", f"Ошибка отправки сообщения поддержки админу {admin_id}", str(e))
    
    if sent_count > 0:
        await message.answer(
            "✅ Ваше сообщение отправлено администраторам.\n"
            "Ожидайте ответа в ближайшее время."
        )
        log_user_action(message.from_user, f"Отправил сообщение в поддержку: {message.text[:50] if message.text else 'Медиа'}")
    else:
        await message.answer(
            "❌ К сожалению, не удалось отправить сообщение администраторам.\n"
            "Попробуйте позже."
        )
    
    await state.clear()


@dp.callback_query(F.data.startswith("support_read_"))
async def handle_support_read(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Прочитать и ответить'"""
    if not is_admin(callback.from_user.id) and callback.from_user.id != CREATOR_ID:
        await callback.answer("❌ У вас нет прав для этого действия.", show_alert=True)
        return
    
    # Извлекаем ID пользователя из callback_data
    user_id = int(callback.data.split("_")[-1])
    
    # Проверяем, не занят ли уже этот диалог другим админом
    if user_id in active_support_dialogs:
        await callback.answer("⚠️ Этот диалог уже обрабатывается другим администратором.", show_alert=True)
        return
    
    # Сохраняем информацию о диалоге
    active_support_dialogs[user_id] = {
        "admin_id": callback.from_user.id,
        "admin_message_id": callback.message.message_id
    }
    
    # Получаем информацию о пользователе
    user_profile = get_user_profile(user_id)
    if user_profile:
        user_info = f"{user_profile['name']} (@{user_profile['username'] if user_profile['username'] != 'NA' else 'отсутствует'})"
    else:
        user_info = f"ID: {user_id}"
    
    # Обновляем сообщение админу с кнопкой "Завершить диалог"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Завершить диалог", callback_data=f"support_close_{user_id}")]
    ])
    
    await callback.message.edit_text(
        f"✅ Вы взяли диалог в обработку\n\n"
        f"👤 Пользователь: {user_info}\n"
        f"🆔 ID: {user_id}\n\n"
        f"Напишите ответ пользователю:",
        reply_markup=keyboard
    )
    
    await state.update_data(user_id=user_id, original_message_id=callback.message.message_id)
    await state.set_state(SupportStates.admin_waiting_for_reply)
    
    log_admin_action(callback.from_user, f"Взял диалог поддержки с пользователем {user_id}")
    await callback.answer()


@dp.message(SupportStates.admin_waiting_for_reply)
async def process_admin_reply(message: Message, state: FSMContext):
    """Обработка ответа админа пользователю"""
    if not is_admin(message.from_user.id) and message.from_user.id != CREATOR_ID:
        await state.clear()
        return
    
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id or user_id not in active_support_dialogs:
        await message.answer("❌ Диалог не найден или был завершен.")
        await state.clear()
        return
    
    # Проверяем, что отвечает тот же админ, который взял диалог
    if active_support_dialogs[user_id]["admin_id"] != message.from_user.id:
        await message.answer("❌ Этот диалог обрабатывается другим администратором.")
        await state.clear()
        return
    
    admin_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or "Администратор"
    
    # Отправляем ответ пользователю с кнопкой "Дополнить"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дополнить", callback_data=f"support_add_{user_id}_{message.from_user.id}")]
    ])
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"💬 Ответ от администратора:\n\n{message.text}",
            reply_markup=keyboard
        )
        
        # Отправляем подтверждение админу с кнопкой "Завершить диалог"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Завершить диалог", callback_data=f"support_close_{user_id}")]
        ])
        
        await message.answer(
            f"✅ Ответ отправлен пользователю (ID: {user_id})",
            reply_markup=keyboard
        )
        
        log_admin_action(message.from_user, f"Ответил пользователю {user_id} в поддержке")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки ответа: {str(e)}")
        log_error("SUPPORT_REPLY", f"Ошибка отправки ответа пользователю {user_id}", str(e))
    
    await state.clear()


@dp.callback_query(F.data.startswith("support_add_"))
async def handle_support_add(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Дополнить' пользователем"""
    # Формат: support_add_{user_id}_{admin_id}
    parts = callback.data.split("_")
    user_id = int(parts[2])
    admin_id = int(parts[3])
    
    # Проверяем, что нажал правильный пользователь
    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не ваше сообщение.", show_alert=True)
        return
    
    # Проверяем, что диалог еще активен
    if user_id not in active_support_dialogs:
        await callback.answer("❌ Диалог был завершен администратором.", show_alert=True)
        return
    
    # Проверяем, что админ все еще тот же
    if active_support_dialogs[user_id]["admin_id"] != admin_id:
        await callback.answer("❌ Диалог был передан другому администратору.", show_alert=True)
        return
    
    # Убираем префикс из текста сообщения
    prefix = "💬 Ответ от администратора:\n\n"
    message_text = callback.message.text
    if message_text.startswith(prefix):
        message_text = message_text[len(prefix):]
    
    await callback.message.edit_text(
        f"💬 Ответ от администратора:\n\n{message_text}"
    )
    
    await callback.message.answer(
        "📝 Напишите ваше дополнение к сообщению:"
    )
    
    await state.update_data(admin_id=admin_id, user_id=user_id)
    await state.set_state(SupportStates.waiting_for_addition)
    
    await callback.answer()


@dp.message(SupportStates.waiting_for_addition)
async def process_user_addition(message: Message, state: FSMContext):
    """Обработка дополнения от пользователя"""
    if not await check_ban_middleware(message):
        await state.clear()
        return
    
    data = await state.get_data()
    admin_id = data.get("admin_id")
    user_id = data.get("user_id")
    
    # Проверяем, что диалог еще активен
    if user_id not in active_support_dialogs:
        await message.answer("❌ Диалог был завершен администратором.")
        await state.clear()
        return
    
    # Проверяем, что админ все еще тот же
    if active_support_dialogs[user_id]["admin_id"] != admin_id:
        await message.answer("❌ Диалог был передан другому администратору.")
        await state.clear()
        return
    
    user_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or "Без имени"
    
    # Отправляем дополнение админу
    addition_text = (
        f"📝 Дополнение от пользователя\n\n"
        f"👤 Пользователь: {user_name}\n"
        f"🆔 ID: {user_id}\n\n"
        f"💬 Дополнение:\n{message.text or 'Медиа-сообщение'}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ответить", callback_data=f"support_reply_add_{user_id}")],
        [InlineKeyboardButton(text="Завершить диалог", callback_data=f"support_close_{user_id}")]
    ])
    
    try:
        await bot.send_message(
            chat_id=admin_id,
            text=addition_text,
            reply_markup=keyboard
        )
        
        await message.answer("✅ Ваше дополнение отправлено администратору.")
        log_user_action(message.from_user, f"Отправил дополнение в поддержку: {message.text[:50] if message.text else 'Медиа'}")
    except Exception as e:
        await message.answer("❌ Ошибка отправки дополнения.")
        log_error("SUPPORT_ADDITION", f"Ошибка отправки дополнения админу {admin_id}", str(e))
    
    await state.clear()


@dp.callback_query(F.data.startswith("support_reply_add_"))
async def handle_support_reply_to_addition(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Ответить' на дополнение"""
    if not is_admin(callback.from_user.id) and callback.from_user.id != CREATOR_ID:
        await callback.answer("❌ У вас нет прав для этого действия.", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    # Проверяем, что диалог еще активен и админ правильный
    if user_id not in active_support_dialogs:
        await callback.answer("❌ Диалог был завершен.", show_alert=True)
        return
    
    if active_support_dialogs[user_id]["admin_id"] != callback.from_user.id:
        await callback.answer("❌ Этот диалог обрабатывается другим администратором.", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ Вы отвечаете на дополнение. Напишите ответ:"
    )
    
    await state.update_data(user_id=user_id, original_message_id=callback.message.message_id)
    await state.set_state(SupportStates.admin_waiting_for_reply_to_addition)
    
    await callback.answer()


@dp.message(SupportStates.admin_waiting_for_reply_to_addition)
async def process_admin_reply_to_addition(message: Message, state: FSMContext):
    """Обработка ответа админа на дополнение"""
    if not is_admin(message.from_user.id) and message.from_user.id != CREATOR_ID:
        await state.clear()
        return
    
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id or user_id not in active_support_dialogs:
        await message.answer("❌ Диалог не найден или был завершен.")
        await state.clear()
        return
    
    # Проверяем, что отвечает тот же админ
    if active_support_dialogs[user_id]["admin_id"] != message.from_user.id:
        await message.answer("❌ Этот диалог обрабатывается другим администратором.")
        await state.clear()
        return
    
    admin_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or "Администратор"
    
    # Отправляем ответ пользователю с кнопкой "Дополнить"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дополнить", callback_data=f"support_add_{user_id}_{message.from_user.id}")]
    ])
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"💬 Ответ от администратора:\n\n{message.text}",
            reply_markup=keyboard
        )
        
        # Отправляем подтверждение админу с кнопкой "Завершить диалог"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Завершить диалог", callback_data=f"support_close_{user_id}")]
        ])
        
        await message.answer(
            f"✅ Ответ на дополнение отправлен пользователю (ID: {user_id})",
            reply_markup=keyboard
        )
        
        log_admin_action(message.from_user, f"Ответил на дополнение пользователя {user_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки ответа: {str(e)}")
        log_error("SUPPORT_REPLY_ADDITION", f"Ошибка отправки ответа на дополнение пользователю {user_id}", str(e))
    
    await state.clear()


@dp.callback_query(F.data.startswith("support_close_"))
async def handle_support_close(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Завершить диалог'"""
    if not is_admin(callback.from_user.id) and callback.from_user.id != CREATOR_ID:
        await callback.answer("❌ У вас нет прав для этого действия.", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    # Проверяем, что диалог существует и админ правильный
    if user_id not in active_support_dialogs:
        await callback.answer("❌ Диалог уже завершен.", show_alert=True)
        return
    
    if active_support_dialogs[user_id]["admin_id"] != callback.from_user.id:
        await callback.answer("❌ Вы не можете завершить чужой диалог.", show_alert=True)
        return
    
    # Удаляем диалог из активных
    del active_support_dialogs[user_id]
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            chat_id=user_id,
            text="✅ Диалог с поддержкой завершен администратором.\n"
                 "Если у вас возникнут новые вопросы, используйте команду /contact"
        )
    except Exception as e:
        log_error("SUPPORT_CLOSE", f"Ошибка отправки уведомления пользователю {user_id}", str(e))
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ Диалог завершен."
    )
    
    log_admin_action(callback.from_user, f"Завершил диалог поддержки с пользователем {user_id}")
    await callback.answer("Диалог завершен")


@dp.message(Command("tonconnect"))
async def cmd_tonconnect(message: Message):
    """Команда /tonconnect - подключение TON кошелька"""
    if not await check_ban_middleware(message):
        return
    
    if not TON_CONNECT_AVAILABLE or tc is None:
        await message.answer(
            "❌ TON Connect недоступен.\n\n"
            "Функция подключения TON кошельков временно недоступна из-за проблем с манифестом.\n"
            "Остальные функции бота работают нормально."
        )
        return
    
    log_user_action(message.from_user, "/tonconnect")
    
    user_id = message.from_user.id
    
    # Проверяем, есть ли уже подключенный кошелек
    connector = None
    if user_id in active_connectors:
        connector = active_connectors[user_id]
    else:
        # Пытаемся загрузить connector из хранилища
        try:
            connector = await tc.init_connector(user_id)
            if connector.wallet:
                active_connectors[user_id] = connector
        except:
            pass
    
    if connector and connector.wallet:
        wallet_address = connector.wallet.account.address.to_str(is_bounceable=False)
        await message.answer(
            f"✅ У вас уже подключен кошелек:\n\n"
            f"Адрес: {wallet_address}\n\n"
            f"Используйте /tonconnect_disconnect для отключения."
        )
        return
    
    try:
        # Получаем список доступных кошельков
        wallets = await tc.get_wallets()
        
        if not wallets:
            await message.answer("❌ Не удалось получить список кошельков. Попробуйте позже.")
            return
        
        # Создаем клавиатуру с кнопками кошельков
        keyboard_buttons = []
        for idx, wallet in enumerate(wallets[:10]):  # Ограничиваем до 10 кошельков
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{wallet.name}",
                    callback_data=f"tonconnect_wallet_{idx}"
                )
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        wallets_text = "🔗 Выберите кошелек для подключения:\n\n"
        for idx, wallet in enumerate(wallets[:10]):
            wallets_text += f"{idx + 1}. {wallet.name}\n"
        
        await message.answer(wallets_text, reply_markup=keyboard)
        
    except Exception as e:
        log_error("TONCONNECT", f"Ошибка получения списка кошельков для пользователя {user_id}", str(e))
        await message.answer("❌ Произошла ошибка при получении списка кошельков. Попробуйте позже.")


@dp.callback_query(F.data.startswith("tonconnect_wallet_"))
async def handle_wallet_selection(callback: CallbackQuery):
    """Обработка выбора кошелька"""
    if not await check_ban_middleware(callback.message):
        await callback.answer()
        return
    
    if not TON_CONNECT_AVAILABLE or tc is None:
        await callback.answer("❌ TON Connect недоступен.", show_alert=True)
        return
    
    try:
        wallet_idx = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id
        
        # Получаем список кошельков
        wallets = await tc.get_wallets()
        
        if wallet_idx >= len(wallets):
            await callback.answer("❌ Кошелек не найден.", show_alert=True)
            return
        
        selected_wallet = wallets[wallet_idx]
        
        # Инициализируем connector для пользователя
        connector = await tc.init_connector(user_id)
        active_connectors[user_id] = connector
        
        # Генерируем URL для подключения
        connect_url = await connector.connect_wallet(selected_wallet)
        
        # Создаем кнопку для открытия ссылки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Подключить кошелек", url=connect_url)],
            [InlineKeyboardButton(text="✅ Я подключил", callback_data=f"tonconnect_check_{user_id}")]
        ])
        
        await callback.message.edit_text(
            f"🔗 Подключение к кошельку {selected_wallet.name}\n\n"
            f"1. Нажмите кнопку ниже для открытия кошелька\n"
            f"2. Подтвердите подключение в кошельке\n"
            f"3. Нажмите '✅ Я подключил' после подтверждения\n\n"
            f"⏱ Ожидание подключения...",
            reply_markup=keyboard
        )
        
        await callback.answer()
        
        # Запускаем проверку подключения в фоне
        asyncio.create_task(check_wallet_connection(user_id, connector))
        
    except Exception as e:
        log_error("TONCONNECT_SELECT", f"Ошибка выбора кошелька для пользователя {callback.from_user.id}", str(e))
        await callback.answer("❌ Произошла ошибка. Попробуйте снова.", show_alert=True)


async def check_wallet_connection(user_id: int, connector):
    """Проверяет подключение кошелька"""
    try:
        print(f"[TONCONNECT] Начало проверки подключения для пользователя {user_id}")
        async with connector.connect_wallet_context() as response:
            print(f"[TONCONNECT] Получен ответ для пользователя {user_id}: {type(response)}")
            if isinstance(response, TonConnectError):
                if isinstance(response, UserRejectsError):
                    await bot.send_message(
                        chat_id=user_id,
                        text="❌ Вы отменили подключение кошелька."
                    )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"❌ Ошибка подключения: {response.message}"
                    )
            else:
                # Успешное подключение
                wallet_address = response.account.address.to_str(is_bounceable=False)
                
                # Обновляем connector в словаре
                active_connectors[user_id] = connector
                
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"✅ Кошелек успешно подключен!\n\n"
                        f"Адрес: {wallet_address}\n\n"
                        f"Используйте /tonconnect_disconnect для отключения."
                    )
                )
                log_user_action(
                    type('obj', (object,), {'id': user_id})(),
                    f"Подключил TON кошелек: {wallet_address}"
                )
                print(f"[TONCONNECT] Кошелек успешно подключен для пользователя {user_id}: {wallet_address}")
    except Exception as e:
        error_msg = str(e)
        print(f"[TONCONNECT] Ошибка проверки подключения для пользователя {user_id}: {error_msg}")
        log_error("TONCONNECT_CHECK", f"Ошибка проверки подключения для пользователя {user_id}", error_msg)
        
        # Пытаемся проверить подключение через хранилище
        try:
            connector_reload = await tc.init_connector(user_id)
            if connector_reload.wallet:
                wallet_address = connector_reload.wallet.account.address.to_str(is_bounceable=False)
                wallet_address_escaped = wallet_address.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
                active_connectors[user_id] = connector_reload
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"✅ Кошелек подключен!\n\n"
                        f"Адрес: {wallet_address}\n\n"
                        f"Используйте /tonconnect_disconnect для отключения."
                    )
                )
                print(f"[TONCONNECT] Кошелек найден через хранилище для пользователя {user_id}")
                return
        except Exception as reload_error:
            print(f"[TONCONNECT] Ошибка перезагрузки connector: {reload_error}")
        
        if user_id in active_connectors:
            del active_connectors[user_id]


@dp.callback_query(F.data.startswith("tonconnect_check_"))
async def handle_manual_check(callback: CallbackQuery):
    """Ручная проверка подключения кошелька"""
    if not TON_CONNECT_AVAILABLE or tc is None:
        await callback.answer("❌ TON Connect недоступен.", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[-1])
    
    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не ваше подключение.", show_alert=True)
        return
    
    # Всегда перезагружаем connector из хранилища для актуальных данных
    connector = None
    if user_id in active_connectors:
        connector = active_connectors[user_id]
    
    try:
        connector = await tc.init_connector(user_id)
        active_connectors[user_id] = connector
    except Exception as e:
        print(f"[TONCONNECT] Ошибка перезагрузки connector для проверки: {e}")
        await callback.answer("❌ Ошибка проверки подключения. Попробуйте позже.", show_alert=True)
        return
    
    if connector.wallet:
        wallet_address = connector.wallet.account.address.to_str(is_bounceable=False)
        await callback.message.edit_text(
            f"✅ Кошелек подключен!\n\n"
            f"Адрес: {wallet_address}\n\n"
            f"Используйте /tonconnect_disconnect для отключения."
        )
        await callback.answer("✅ Кошелек подключен!")
        log_user_action(
            type('obj', (object,), {'id': user_id})(),
            f"Подключил TON кошелек через ручную проверку: {wallet_address}"
        )
    else:
        await callback.answer("⏳ Подключение еще не завершено. Подождите несколько секунд и нажмите снова.", show_alert=True)


@dp.message(Command("tonconnect_disconnect"))
async def cmd_tonconnect_disconnect(message: Message):
    """Команда /tonconnect_disconnect - отключение TON кошелька"""
    if not await check_ban_middleware(message):
        return
    
    if not TON_CONNECT_AVAILABLE or tc is None:
        await message.answer(
            "❌ TON Connect недоступен.\n\n"
            "Функция подключения TON кошельков временно недоступна из-за проблем с манифестом.\n"
            "Остальные функции бота работают нормально."
        )
        return
    
    log_user_action(message.from_user, "/tonconnect_disconnect")
    
    user_id = message.from_user.id
    
    # Проверяем подключение через хранилище, если в памяти нет
    connector = None
    if user_id in active_connectors:
        connector = active_connectors[user_id]
    else:
        try:
            connector = await tc.init_connector(user_id)
        except:
            pass
    
    if not connector or not connector.wallet:
        await message.answer("❌ У вас нет подключенного кошелька.")
        return
    
    try:
        await connector.disconnect_wallet()
        if user_id in active_connectors:
            del active_connectors[user_id]
        
        await message.answer("✅ Кошелек успешно отключен.")
        log_user_action(message.from_user, "Отключил TON кошелек")
        
    except Exception as e:
        log_error("TONCONNECT_DISCONNECT", f"Ошибка отключения кошелька для пользователя {user_id}", str(e))
        await message.answer("❌ Произошла ошибка при отключении кошелька.")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    if not await check_ban_middleware(message):
        return
    
    log_user_action(message.from_user, "/help")
    
    user_id = message.from_user.id
    status = get_user_status(user_id)
    
    help_text = "📋 Доступные команды:\n\n"
    
    # Общие команды для всех
    help_text += "👤 Для всех пользователей:\n"
    help_text += "/start - запуск бота\n"
    help_text += "/profile - профиль пользователя\n"
    help_text += "/balance - баланс в TPCoin\n"
    help_text += "/transfer количество id - перевод TPCoin другому пользователю\n"
    help_text += "/myach - список достижений\n"
    help_text += "/contact - связаться с поддержкой\n"
    if TON_CONNECT_AVAILABLE:
        help_text += "/tonconnect - подключить TON кошелек\n"
        help_text += "/tonconnect_disconnect - отключить TON кошелек\n"
    help_text += "/help - список команд\n\n"
    
    # Команды для админов и создателя
    if status in ["Admin", "Creator"]:
        help_text += "🔧 Для администраторов:\n"
        help_text += "/ban id - заблокировать пользователя\n"
        help_text += "/unban id - разблокировать пользователя\n"
        help_text += "/banlist - список забаненных пользователей\n"
        help_text += "/tempban id время причина - временный бан\n"
        help_text += "/massban id1 id2 ... - массовый бан\n"
        help_text += "/achlist - список всех достижений\n"
        help_text += "/sendach idДОСТИЖЕНИЯ idАККАУНТА - выдать достижение\n"
        help_text += "/removeach idДОСТИЖЕНИЯ idПОЛЬЗОВАТЕЛЯ - удалить достижение у пользователя\n"
        help_text += "/masssendach idДОСТИЖЕНИЯ - массовая выдача достижения\n"
        help_text += "/addbalance сумма id - добавить баланс пользователю\n"
        help_text += "/removebalance сумма id - снять баланс у пользователя\n"
        help_text += "/topbalance - топ пользователей по балансу\n"
        help_text += "/sendsms текст - рассылка всем пользователям\n"
        help_text += "/sendprivat текст --id123456789 - отправка сообщения одному пользователю\n"
        help_text += "/search id - информация о пользователе\n"
        help_text += "/userlogs - последние 20 строк логов пользователей\n"
        help_text += "/errorlogs - последние 20 строк логов ошибок\n"
        help_text += "/ping - время отклика бота\n\n"
    
    # Команды только для создателя
    if status == "Creator":
        help_text += "👑 Только для создателя:\n"
        help_text += "/addadmin id - назначить администратора\n"
        help_text += "/unadmin id - разжаловать администратора\n"
        help_text += "/adminlist - список всех администраторов\n"
        help_text += "/sendcoin количество id - перевести TPCoin\n"
        help_text += "/masssendcoin сумма - массовая выдача монет всем\n"
        help_text += "/newach id название - создать новое достижение\n"
        help_text += "/deleteach idДОСТИЖЕНИЯ - удалить достижение из системы\n"
        help_text += "/adminlogs - логи администраторов\n"
        help_text += "/systemlogs - системные логи\n"
        help_text += "/test - статистика системы\n"
    
    await message.answer(help_text)


# ========== КОМАНДЫ ДЛЯ ADMIN И CREATOR ==========

async def check_admin(message: Message) -> bool:
    """Проверяет права администратора"""
    user_id = message.from_user.id
    if user_id != CREATOR_ID and not is_admin(user_id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return False
    return True


@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    """Команда /ban"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/ban")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer("Использование: /ban id или /ban username")
        return
    
    identifier = args[0]
    user_info = await get_user_by_id_or_username_async(identifier)
    
    if not user_info:
        await message.answer(f"Пользователь {identifier} не найден.")
        return
    
    target_id = user_info[0]
    
    if int(target_id) == CREATOR_ID:
        await message.answer("❌ Нельзя забанить создателя бота!")
        return
    
    if int(target_id) == message.from_user.id:
        await message.answer("❌ Нельзя забанить самого себя!")
        return
    
    if is_banned(int(target_id)):
        await message.answer(f"Пользователь {identifier} уже заблокирован.")
        return
    
    # Создаем объект пользователя для ban_user
    class FakeUser:
        def __init__(self, user_id, name, username):
            self.id = int(user_id)
            parts = name.split()
            self.first_name = parts[0] if parts else "NA"
            self.last_name = " ".join(parts[1:]) if len(parts) > 1 else None
            self.username = username if username != "NA" else None
    
    target_user = FakeUser(user_info[0], user_info[1], user_info[2])
    ban_user(message.from_user, target_user)
    
    log_admin_command(message.from_user, f"/ban {target_id}")
    await message.answer(f"✅ Пользователь {identifier} заблокирован.")


@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    """Команда /unban"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/unban")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer("Использование: /unban id или /unban username")
        return
    
    identifier = args[0]
    user_info = await get_user_by_id_or_username_async(identifier)
    
    if not user_info:
        await message.answer(f"Пользователь {identifier} не найден.")
        return
    
    target_id = user_info[0]
    
    if unban_user(message.from_user, target_id):
        log_admin_command(message.from_user, f"/unban {target_id}")
        await message.answer(f"✅ Пользователь {identifier} разблокирован.")
    else:
        await message.answer(f"Пользователь {identifier} не был заблокирован.")


@dp.message(Command("sendsms"))
async def cmd_sendsms(message: Message):
    """Команда /sendsms"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/sendsms")
    
    text = message.text.replace("/sendsms", "").strip()
    if not text:
        await message.answer("Использование: /sendsms текст сообщения")
        return
    
    log_admin_command(message.from_user, f"/sendsms {text[:50]}")
    
    users = get_all_users()
    total = len(users)
    success = 0
    errors = 0
    
    await message.answer("Начинаю рассылку...")
    
    for user_id in users:
        try:
            await bot.send_message(chat_id=int(user_id), text=text)
            success += 1
        except Exception as e:
            errors += 1
            log_error("SENDSMS", f"Ошибка отправки сообщения пользователю {user_id}", str(e))
            log_system_event("BOT", f"Ошибка отправки сообщения пользователю {user_id}: {str(e)}")
        await asyncio.sleep(0.05)  # Небольшая задержка для избежания лимитов
    
    report = (
        f"📊 Отчет о рассылке:\n\n"
        f"Всего пользователей: {total}\n"
        f"Успешно отправлено: {success}\n"
        f"Ошибка доставки: {errors}"
    )
    await message.answer(report)


@dp.message(Command("sendprivat"))
async def cmd_sendprivat(message: Message):
    """Команда /sendprivat"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/sendprivat")
    
    text = message.text.replace("/sendprivat", "").strip()
    
    if "--id" not in text:
        await message.answer("Использование: /sendprivat текст --id123456789")
        return
    
    parts = text.split("--id")
    if len(parts) != 2:
        await message.answer("Использование: /sendprivat текст --id123456789")
        return
    
    message_text = parts[0].strip()
    user_id = parts[1].strip()
    
    if not message_text:
        await message.answer("Текст сообщения не может быть пустым.")
        return
    
    try:
        await bot.send_message(chat_id=int(user_id), text=message_text)
        log_admin_command(message.from_user, f"/sendprivat --id{user_id}")
        await message.answer(f"✅ Сообщение отправлено пользователю {user_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {str(e)}")
        log_error("SENDPRIVAT", f"Ошибка отправки приватного сообщения пользователю {user_id}", str(e))
        log_system_event("BOT", f"Ошибка отправки приватного сообщения: {str(e)}")


@dp.message(Command("sendach"))
async def cmd_sendach(message: Message):
    """Команда /sendach"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/sendach")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if len(args) < 2:
        await message.answer("Использование: /sendach idДОСТИЖЕНИЯ idАККАУНТА")
        return
    
    ach_id = args[0]
    target_id = args[1]
    
    # Получаем информацию о достижении
    ach_name = "Неизвестное достижение"
    achievements = get_all_achievements()
    for ach in achievements:
        if ach["id"] == ach_id:
            ach_name = ach["name"]
            break
    
    # Получаем информацию о пользователе
    user_info = await get_user_by_id_or_username_async(target_id)
    if not user_info:
        await message.answer(f"Пользователь {target_id} не найден.")
        return
    
    class FakeUser:
        def __init__(self, user_id, name, username):
            self.id = int(user_id)
            parts = name.split()
            self.first_name = parts[0] if parts else "NA"
            self.last_name = " ".join(parts[1:]) if len(parts) > 1 else None
            self.username = username if username != "NA" else None
    
    target_user = FakeUser(user_info[0], user_info[1], user_info[2])
    add_achievement(message.from_user, target_user, ach_id, ach_name)
    
    # Отправляем уведомление пользователю
    try:
        await bot.send_message(
            chat_id=int(target_id),
            text="🎉 У Вас новое достижение. Поздравляем!"
        )
    except:
        pass
    
    await message.answer(f"✅ Достижение '{ach_name}' выдано пользователю {target_id}")


@dp.message(Command("removeach"))
async def cmd_removeach(message: Message):
    """Команда /removeach - удалить достижение у пользователя"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/removeach")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if len(args) < 2:
        await message.answer("Использование: /removeach idДОСТИЖЕНИЯ idПОЛЬЗОВАТЕЛЯ")
        return
    
    ach_id = args[0]
    identifier = args[1]
    
    # Получаем информацию о пользователе
    user_info = await get_user_by_id_or_username_async(identifier)
    if not user_info:
        await message.answer(f"❌ Пользователь {identifier} не найден.")
        return
    
    target_id = user_info[0]
    
    # Получаем информацию о достижении
    ach_name = "Неизвестное достижение"
    achievements = get_all_achievements()
    for ach in achievements:
        if ach["id"] == ach_id:
            ach_name = ach["name"]
            break
    
    # Проверяем, есть ли у пользователя это достижение
    user_achievements = get_user_achievements(int(target_id))
    has_achievement = any(ach['id'] == ach_id for ach in user_achievements)
    
    if not has_achievement:
        await message.answer(f"❌ У пользователя {identifier} нет достижения с ID {ach_id}.")
        return
    
    if remove_achievement_from_user(message.from_user, target_id, ach_id):
        log_admin_command(message.from_user, f"/removeach {ach_id} {target_id}")
        
        # Отправляем уведомление пользователю
        try:
            await bot.send_message(
                chat_id=int(target_id),
                text=f"⚠️ У вас удалено достижение: {ach_name}"
            )
        except:
            pass
        
        await message.answer(f"✅ Достижение '{ach_name}' удалено у пользователя {identifier}")
    else:
        await message.answer(f"❌ Ошибка при удалении достижения.")


@dp.message(Command("search"))
async def cmd_search(message: Message):
    """Команда /search"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/search")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer("Использование: /search id или /search username")
        return
    
    identifier = args[0]
    user_info = await get_user_by_id_or_username_async(identifier)
    
    if not user_info:
        await message.answer(f"Пользователь {identifier} не найден.")
        return
    
    user_id = user_info[0]
    profile = get_user_profile(int(user_id))
    
    if not profile:
        await message.answer("Профиль не найден.")
        return
    
    balance = get_user_balance(int(user_id))
    achievements = get_user_achievements(int(user_id))
    
    info_text = (
        f"🔍 Информация о пользователе\n\n"
        f"Имя и Фамилия: {profile['name']}\n"
        f"Username: @{profile['username'] if profile['username'] != 'NA' else 'отсутствует'}\n"
        f"Telegram ID: {profile['id']}\n"
        f"Дата первого запуска: {profile['first_start']}\n"
        f"Баланс: {balance} TPCoin\n\n"
    )
    
    if achievements:
        info_text += "🏆 Достижения:\n"
        for ach in achievements:
            info_text += f"• {ach['name']} (ID: {ach['id']})\n"
    else:
        info_text += "Достижений нет."
    
    await message.answer(info_text)


@dp.message(Command("userlogs"))
async def cmd_userlogs(message: Message):
    """Команда /userlogs"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/userlogs")
    
    logs = get_last_logs("user_logs", 20)
    
    if not logs:
        await message.answer("Логи пусты.")
        return
    
    log_text = "📋 Последние 20 строк логов пользователей:\n\n"
    log_text += "".join(logs)
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(log_text) > 4096:
        parts = [log_text[i:i+4096] for i in range(0, len(log_text), 4096)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(log_text)


@dp.message(Command("errorlogs"))
async def cmd_errorlogs(message: Message):
    """Команда /errorlogs"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/errorlogs")
    
    logs = get_last_logs("error_logs", 20)
    
    if not logs:
        await message.answer("Логи ошибок пусты.")
        return
    
    log_text = "📋 Последние 20 строк логов ошибок:\n\n"
    log_text += "".join(logs)
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(log_text) > 4096:
        parts = [log_text[i:i+4096] for i in range(0, len(log_text), 4096)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(log_text)


@dp.message(Command("ping"))
async def cmd_ping(message: Message):
    """Команда /ping"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/ping")
    
    start_time = time.time()
    try:
        await bot.get_me()
        end_time = time.time()
        ping_ms = round((end_time - start_time) * 1000, 2)
        await message.answer(f"🏓 Pong! Время отклика: {ping_ms} мс")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("achlist"))
async def cmd_achlist(message: Message):
    """Команда /achlist - список всех достижений"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/achlist")
    
    achievements = get_all_achievements()
    
    if not achievements:
        await message.answer("Список достижений пуст.")
        return
    
    ach_text = "🏆 Список всех достижений:\n\n"
    for ach in achievements:
        ach_text += f"• {ach['name']} (ID: {ach['id']})\n"
        if ach['created'] != "NA":
            ach_text += f"  Создано: {ach['created']}\n"
        ach_text += "\n"
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(ach_text) > 4096:
        parts = [ach_text[i:i+4096] for i in range(0, len(ach_text), 4096)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(ach_text)


@dp.message(Command("banlist"))
async def cmd_banlist(message: Message):
    """Команда /banlist - список забаненных пользователей"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/banlist")
    
    banned = get_all_banned_users()
    
    if not banned:
        await message.answer("Список забаненных пользователей пуст.")
        return
    
    ban_text = "🚫 Список забаненных пользователей:\n\n"
    for user in banned:
        ban_text += f"• {user['name']} (@{user['username'] if user['username'] != 'NA' else 'отсутствует'})\n"
        ban_text += f"  ID: {user['id']}\n"
        ban_text += f"  Забанен: {user['banned_date']}\n"
        if user['banned_by'] != "NA":
            ban_text += f"  Забанен администратором: {user['banned_by']}\n"
        ban_text += "\n"
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(ban_text) > 4096:
        parts = [ban_text[i:i+4096] for i in range(0, len(ban_text), 4096)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(ban_text)


@dp.message(Command("addbalance"))
async def cmd_addbalance(message: Message):
    """Команда /addbalance - добавить баланс пользователю (для админов)"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/addbalance")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if len(args) < 2:
        await message.answer("Использование: /addbalance сумма id или /addbalance сумма username")
        return
    
    try:
        amount = int(args[0])
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительным числом.")
            return
    except ValueError:
        await message.answer("❌ Сумма должна быть числом.")
        return
    
    identifier = args[1]
    user_info = await get_user_by_id_or_username_async(identifier)
    
    if not user_info:
        await message.answer(f"❌ Пользователь {identifier} не найден.")
        return
    
    target_id = int(user_info[0])
    old_balance = get_user_balance(target_id)
    add_user_balance(target_id, amount)
    new_balance = get_user_balance(target_id)
    
    log_admin_command(message.from_user, f"/addbalance {amount} {target_id}")
    
    # Отправляем уведомление пользователю
    try:
        await bot.send_message(
            chat_id=target_id,
            text=f"💰 Ваш баланс пополнен администратором на {amount} TPCoin\n"
                 f"Новый баланс: {new_balance} TPCoin"
        )
    except:
        pass
    
    await message.answer(
        f"✅ Баланс пользователя {user_info[1]} пополнен на {amount} TPCoin\n"
        f"Старый баланс: {old_balance}\n"
        f"Новый баланс: {new_balance}"
    )


@dp.message(Command("removebalance"))
async def cmd_removebalance(message: Message):
    """Команда /removebalance - снять баланс у пользователя (для админов и создателя)"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/removebalance")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if len(args) < 2:
        await message.answer("Использование: /removebalance сумма id или /removebalance сумма username")
        return
    
    try:
        amount = int(args[0])
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительным числом.")
            return
    except ValueError:
        await message.answer("❌ Сумма должна быть числом.")
        return
    
    identifier = args[1]
    user_info = await get_user_by_id_or_username_async(identifier)
    
    if not user_info:
        await message.answer(f"❌ Пользователь {identifier} не найден.")
        return
    
    target_id = int(user_info[0])
    old_balance = get_user_balance(target_id)
    new_balance = remove_user_balance(target_id, amount)
    
    log_admin_command(message.from_user, f"/removebalance {amount} {target_id}")
    
    # Отправляем уведомление пользователю
    try:
        await bot.send_message(
            chat_id=target_id,
            text=f"⚠️ С вашего баланса снято {amount} TPCoin администратором\n"
                 f"Новый баланс: {new_balance} TPCoin"
        )
    except:
        pass
    
    await message.answer(
        f"✅ С баланса пользователя {user_info[1]} снято {amount} TPCoin\n"
        f"Старый баланс: {old_balance}\n"
        f"Новый баланс: {new_balance}"
    )


@dp.message(Command("topbalance"))
async def cmd_topbalance(message: Message):
    """Команда /topbalance - топ пользователей по балансу"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/topbalance")
    
    top_users = get_top_users_by_balance(20)
    
    if not top_users:
        await message.answer("Нет пользователей с балансом.")
        return
    
    top_text = "🏆 Топ пользователей по балансу:\n\n"
    
    for idx, (user_id, balance) in enumerate(top_users, 1):
        profile = get_user_profile(user_id)
        if profile:
            username = f"@{profile['username']}" if profile['username'] != 'NA' else "отсутствует"
            top_text += f"{idx}. {profile['name']} ({username})\n"
        else:
            top_text += f"{idx}. ID: {user_id}\n"
        top_text += f"   💰 {balance} TPCoin\n\n"
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(top_text) > 4096:
        parts = [top_text[i:i+4096] for i in range(0, len(top_text), 4096)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(top_text)


# ========== КОМАНДЫ ТОЛЬКО ДЛЯ CREATOR ==========

async def check_creator(message: Message) -> bool:
    """Проверяет права создателя"""
    if message.from_user.id != CREATOR_ID:
        await message.answer("❌ Эта команда доступна только создателю бота.")
        return False
    return True


@dp.message(Command("addadmin"))
async def cmd_addadmin(message: Message):
    """Команда /addadmin"""
    if not await check_creator(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/addadmin")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer("Использование: /addadmin id или /addadmin username")
        return
    
    identifier = args[0]
    user_info = await get_user_by_id_or_username_async(identifier)
    
    if not user_info:
        await message.answer(f"Пользователь {identifier} не найден.")
        return
    
    target_id = user_info[0]
    
    if int(target_id) == CREATOR_ID:
        await message.answer("Создатель уже имеет все права.")
        return
    
    if is_admin(int(target_id)):
        await message.answer(f"Пользователь {identifier} уже является администратором.")
        return
    
    class FakeUser:
        def __init__(self, user_id, name, username):
            self.id = int(user_id)
            parts = name.split()
            self.first_name = parts[0] if parts else "NA"
            self.last_name = " ".join(parts[1:]) if len(parts) > 1 else None
            self.username = username if username != "NA" else None
    
    target_user = FakeUser(user_info[0], user_info[1], user_info[2])
    add_admin(message.from_user, target_user)
    
    await message.answer(f"✅ Пользователь {identifier} назначен администратором.")


@dp.message(Command("unadmin"))
async def cmd_unadmin(message: Message):
    """Команда /unadmin"""
    if not await check_creator(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/unadmin")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer("Использование: /unadmin id или /unadmin username")
        return
    
    identifier = args[0]
    user_info = await get_user_by_id_or_username_async(identifier)
    
    if not user_info:
        await message.answer(f"Пользователь {identifier} не найден.")
        return
    
    target_id = user_info[0]
    
    if remove_admin(message.from_user, target_id):
        await message.answer(f"✅ Пользователь {identifier} разжалован из администраторов.")
    else:
        await message.answer(f"Пользователь {identifier} не является администратором.")


@dp.message(Command("sendcoin"))
async def cmd_sendcoin(message: Message):
    """Команда /sendcoin"""
    if not await check_creator(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/sendcoin")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if len(args) < 2:
        await message.answer("Использование: /sendcoin кол-во_монет id или /sendcoin кол-во_монет username")
        return
    
    try:
        amount = int(args[0])
        if amount <= 0:
            await message.answer("Количество монет должно быть положительным числом.")
            return
    except ValueError:
        await message.answer("Количество монет должно быть числом.")
        return
    
    identifier = args[1]
    user_info = await get_user_by_id_or_username_async(identifier)
    
    if not user_info:
        await message.answer(f"Пользователь {identifier} не найден.")
        return
    
    target_id = user_info[0]
    add_user_balance(int(target_id), amount)
    
    log_admin_command(message.from_user, f"/sendcoin {amount} {target_id}")
    
    # Отправляем уведомление пользователю
    try:
        await bot.send_message(
            chat_id=int(target_id),
            text=f"💰 Ваш баланс пополнен на {amount} TPCoin"
        )
    except:
        pass
    
    await message.answer(f"✅ Пользователю {identifier} переведено {amount} TPCoin")


@dp.message(Command("masssendcoin"))
async def cmd_masssendcoin(message: Message):
    """Команда /masssendcoin - массовая выдача монет всем пользователям (только для Creator)"""
    if not await check_creator(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/masssendcoin")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer("Использование: /masssendcoin сумма")
        return
    
    try:
        amount = int(args[0])
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительным числом.")
            return
    except ValueError:
        await message.answer("❌ Сумма должна быть числом.")
        return
    
    users = get_all_users()
    total = len(users)
    success = 0
    errors = 0
    
    await message.answer(f"Начинаю массовую выдачу {amount} TPCoin {total} пользователям...")
    
    for user_id_str in users:
        try:
            user_id = int(user_id_str)
            add_user_balance(user_id, amount)
            success += 1
            
            # Отправляем уведомление пользователю
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"💰 Массовая выдача монет!\nВаш баланс пополнен на {amount} TPCoin"
                )
            except:
                pass
            
            await asyncio.sleep(0.05)  # Небольшая задержка
        except Exception as e:
            errors += 1
            log_error("MASSSENDCOIN", f"Ошибка выдачи монет пользователю {user_id_str}", str(e))
    
    log_admin_command(message.from_user, f"/masssendcoin {amount}")
    
    report = (
        f"📊 Отчет о массовой выдаче:\n\n"
        f"Всего пользователей: {total}\n"
        f"Успешно: {success}\n"
        f"Ошибок: {errors}\n"
        f"Сумма на пользователя: {amount} TPCoin"
    )
    await message.answer(report)


@dp.message(Command("masssendach"))
async def cmd_masssendach(message: Message):
    """Команда /masssendach - массовая выдача достижения всем пользователям"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/masssendach")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer("Использование: /masssendach idДОСТИЖЕНИЯ")
        return
    
    ach_id = args[0]
    
    # Получаем информацию о достижении
    ach_name = "Неизвестное достижение"
    achievements = get_all_achievements()
    for ach in achievements:
        if ach["id"] == ach_id:
            ach_name = ach["name"]
            break
    
    users = get_all_users()
    total = len(users)
    success = 0
    errors = 0
    
    await message.answer(f"Начинаю массовую выдачу достижения '{ach_name}' {total} пользователям...")
    
    for user_id_str in users:
        try:
            user_id = int(user_id_str)
            user_info = get_user_profile(user_id)
            
            if user_info:
                class FakeUser:
                    def __init__(self, user_id, name, username):
                        self.id = int(user_id)
                        parts = name.split()
                        self.first_name = parts[0] if parts else "NA"
                        self.last_name = " ".join(parts[1:]) if len(parts) > 1 else None
                        self.username = username if username != "NA" else None
                
                target_user = FakeUser(user_id, user_info['name'], user_info['username'])
                add_achievement(message.from_user, target_user, ach_id, ach_name)
                success += 1
                
                # Отправляем уведомление пользователю
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"🎉 Массовая выдача достижения!\nВы получили: {ach_name}"
                    )
                except:
                    pass
                
                await asyncio.sleep(0.05)  # Небольшая задержка
        except Exception as e:
            errors += 1
            log_error("MASSSENDACH", f"Ошибка выдачи достижения пользователю {user_id_str}", str(e))
    
    log_admin_command(message.from_user, f"/masssendach {ach_id}")
    
    report = (
        f"📊 Отчет о массовой выдаче достижения:\n\n"
        f"Достижение: {ach_name} (ID: {ach_id})\n"
        f"Всего пользователей: {total}\n"
        f"Успешно: {success}\n"
        f"Ошибок: {errors}"
    )
    await message.answer(report)


@dp.message(Command("massban"))
async def cmd_massban(message: Message):
    """Команда /massban - массовый бан пользователей"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/massban")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer("Использование: /massban id1 id2 id3 ... (через пробел)")
        return
    
    banned_count = 0
    errors = 0
    already_banned = 0
    
    await message.answer(f"Начинаю массовый бан {len(args)} пользователей...")
    
    for identifier in args:
        try:
            user_info = await get_user_by_id_or_username_async(identifier)
            
            if not user_info:
                errors += 1
                continue
            
            target_id = int(user_info[0])
            
            if target_id == CREATOR_ID:
                continue
            
            if target_id == message.from_user.id:
                continue
            
            if is_banned(target_id):
                already_banned += 1
                continue
            
            class FakeUser:
                def __init__(self, user_id, name, username):
                    self.id = int(user_id)
                    parts = name.split()
                    self.first_name = parts[0] if parts else "NA"
                    self.last_name = " ".join(parts[1:]) if len(parts) > 1 else None
                    self.username = username if username != "NA" else None
            
            target_user = FakeUser(user_info[0], user_info[1], user_info[2])
            ban_user(message.from_user, target_user)
            banned_count += 1
            
        except Exception as e:
            errors += 1
            log_error("MASSBAN", f"Ошибка бана пользователя {identifier}", str(e))
    
    log_admin_command(message.from_user, f"/massban {len(args)} users")
    
    report = (
        f"📊 Отчет о массовом бане:\n\n"
        f"Обработано: {len(args)}\n"
        f"Забанено: {banned_count}\n"
        f"Уже были забанены: {already_banned}\n"
        f"Ошибок: {errors}"
    )
    await message.answer(report)


@dp.message(Command("tempban"))
async def cmd_tempban(message: Message):
    """Команда /tempban - временный бан пользователя"""
    if not await check_admin(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/tempban")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if len(args) < 3:
        await message.answer("Использование: /tempban id время_в_часах причина")
        return
    
    identifier = args[0]
    
    try:
        duration_hours = int(args[1])
        if duration_hours <= 0:
            await message.answer("❌ Время бана должно быть положительным числом часов.")
            return
    except ValueError:
        await message.answer("❌ Время бана должно быть числом.")
        return
    
    reason = " ".join(args[2:])
    
    user_info = await get_user_by_id_or_username_async(identifier)
    
    if not user_info:
        await message.answer(f"❌ Пользователь {identifier} не найден.")
        return
    
    target_id = int(user_info[0])
    
    if target_id == CREATOR_ID:
        await message.answer("❌ Нельзя забанить создателя бота!")
        return
    
    if target_id == message.from_user.id:
        await message.answer("❌ Нельзя забанить самого себя!")
        return
    
    if is_banned(target_id):
        await message.answer(f"Пользователь {identifier} уже заблокирован.")
        return
    
    # Проверяем, есть ли уже временный бан
    if is_temp_banned(target_id):
        await message.answer(f"У пользователя {identifier} уже есть активный временный бан.")
        return
    
    # Баним пользователя
    class FakeUser:
        def __init__(self, user_id, name, username):
            self.id = int(user_id)
            parts = name.split()
            self.first_name = parts[0] if parts else "NA"
            self.last_name = " ".join(parts[1:]) if len(parts) > 1 else None
            self.username = username if username != "NA" else None
    
    target_user = FakeUser(user_info[0], user_info[1], user_info[2])
    ban_user(message.from_user, target_user)
    
    # Добавляем временный бан
    unban_time = add_temp_ban(target_id, duration_hours, reason, message.from_user.id)
    
    log_admin_command(message.from_user, f"/tempban {target_id} {duration_hours}h {reason}")
    
    await message.answer(
        f"✅ Пользователь {identifier} заблокирован временно на {duration_hours} часов.\n"
        f"Причина: {reason}\n"
        f"Автоматический разбан: {unban_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )


@dp.message(Command("newach"))
async def cmd_newach(message: Message):
    """Команда /newach"""
    if not await check_creator(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/newach")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if len(args) < 2:
        await message.answer("Использование: /newach id название")
        return
    
    ach_id = args[0]
    ach_name = " ".join(args[1:])
    
    # Проверяем, существует ли уже достижение с таким ID
    achievements = get_all_achievements()
    for ach in achievements:
        if ach["id"] == ach_id:
            await message.answer(f"Достижение с ID {ach_id} уже существует.")
            return
    
    create_achievement(message.from_user, ach_id, ach_name)
    await message.answer(f"✅ Создано новое достижение: {ach_name} (ID: {ach_id})")


@dp.message(Command("deleteach"))
async def cmd_deleteach(message: Message):
    """Команда /deleteach - удалить достижение из системы (только для Creator)"""
    if not await check_creator(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/deleteach")
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer("Использование: /deleteach idДОСТИЖЕНИЯ")
        return
    
    ach_id = args[0]
    
    # Проверяем, существует ли достижение
    ach_name = None
    achievements = get_all_achievements()
    for ach in achievements:
        if ach["id"] == ach_id:
            ach_name = ach["name"]
            break
    
    if not ach_name:
        await message.answer(f"❌ Достижение с ID {ach_id} не найдено.")
        return
    
    if delete_achievement(message.from_user, ach_id):
        log_admin_command(message.from_user, f"/deleteach {ach_id}")
        await message.answer(f"✅ Достижение '{ach_name}' (ID: {ach_id}) удалено из системы.")
    else:
        await message.answer(f"❌ Ошибка при удалении достижения.")


@dp.message(Command("adminlogs"))
async def cmd_adminlogs(message: Message):
    """Команда /adminlogs"""
    if not await check_creator(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/adminlogs")
    
    logs = get_last_logs("admin_logs", 20)
    
    if not logs:
        await message.answer("Логи пусты.")
        return
    
    log_text = "📋 Последние 20 строк логов администраторов:\n\n"
    log_text += "".join(logs)
    
    if len(log_text) > 4096:
        parts = [log_text[i:i+4096] for i in range(0, len(log_text), 4096)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(log_text)


@dp.message(Command("systemlogs"))
async def cmd_systemlogs(message: Message):
    """Команда /systemlogs"""
    if not await check_creator(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/systemlogs")
    
    logs = get_last_logs("system_logs", 20)
    
    if not logs:
        await message.answer("Логи пусты.")
        return
    
    log_text = "📋 Последние 20 строк системных логов:\n\n"
    log_text += "".join(logs)
    
    if len(log_text) > 4096:
        parts = [log_text[i:i+4096] for i in range(0, len(log_text), 4096)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(log_text)


@dp.message(Command("adminlist"))
async def cmd_adminlist(message: Message):
    """Команда /adminlist - список администраторов (только для CREATOR_ID)"""
    if not await check_creator(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/adminlist")
    
    admins = get_all_admins()
    
    admin_text = "👑 Список администраторов:\n\n"
    
    # Добавляем создателя в начало списка
    creator_profile = get_user_profile(CREATOR_ID)
    if creator_profile:
        admin_text += f"👑 Создатель:\n"
        admin_text += f"• {creator_profile['name']} (@{creator_profile['username'] if creator_profile['username'] != 'NA' else 'отсутствует'})\n"
        admin_text += f"  ID: {creator_profile['id']}\n\n"
    
    if not admins:
        admin_text += "Других администраторов нет."
    else:
        admin_text += "Администраторы:\n"
        for admin in admins:
            admin_text += f"• {admin['name']} (@{admin['username'] if admin['username'] != 'NA' else 'отсутствует'})\n"
            admin_text += f"  ID: {admin['id']}\n"
            if admin['added_date'] != "NA":
                admin_text += f"  Назначен: {admin['added_date']}\n"
            admin_text += "\n"
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(admin_text) > 4096:
        parts = [admin_text[i:i+4096] for i in range(0, len(admin_text), 4096)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(admin_text)


@dp.message(Command("test"))
async def cmd_test(message: Message):
    """Команда /test - статистика системы"""
    if not await check_creator(message):
        return
    
    if not await check_ban_middleware(message):
        return
    
    log_admin_action(message.from_user, "/test")
    
    # Измеряем пинг бота
    start_time = time.time()
    try:
        await bot.get_me()
        end_time = time.time()
        ping_ms = round((end_time - start_time) * 1000, 2)
    except Exception as e:
        ping_ms = f"Ошибка: {str(e)}"
    
    # Получаем статистику из базы данных
    total_users = get_total_users_count()
    new_users_24h = get_new_users_last_24h()
    admins_count = get_admins_count()
    achievements_count = get_achievements_count()
    logs_stats = get_logs_statistics()
    
    # Получаем дополнительную статистику
    from database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Количество забаненных пользователей
    cursor.execute("SELECT COUNT(*) as count FROM blacklist")
    banned_count = cursor.fetchone()["count"]
    
    # Количество пользователей с балансом > 0
    cursor.execute("SELECT COUNT(*) as count FROM balances WHERE balance > 0")
    users_with_balance = cursor.fetchone()["count"]
    
    # Общая сумма всех балансов
    cursor.execute("SELECT SUM(balance) as total FROM balances")
    total_balance = cursor.fetchone()["total"] or 0
    
    # Количество активных временных банов
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT COUNT(*) as count FROM temp_bans WHERE unban_time > ?", (now,))
    active_temp_bans = cursor.fetchone()["count"]
    
    conn.close()
    
    # Размер базы данных
    db_size_kb = round(logs_stats.get("db_size", 0) / 1024, 2)
    db_size_mb = round(db_size_kb / 1024, 2)
    db_size_str = f"{db_size_mb} MB" if db_size_mb >= 1 else f"{db_size_kb} KB"
    
    # Формируем отчет
    report = "🔍 Статистика системы\n\n"
    
    report += f"🏓 Пинг бота: {ping_ms} мс\n\n"
    
    report += "💾 База данных:\n"
    report += f"  Размер: {db_size_str}\n"
    report += f"  Статус: ✅ Подключена\n\n"
    
    report += "📊 Основная статистика:\n"
    report += f"  👥 Всего пользователей: {total_users}\n"
    report += f"  🆕 Новых за 24 часа: {new_users_24h}\n"
    report += f"  👑 Администраторов: {admins_count}\n"
    report += f"  🚫 Забаненных: {banned_count}\n"
    report += f"  ⏰ Активных временных банов: {active_temp_bans}\n"
    report += f"  🏆 Всего достижений: {achievements_count}\n\n"
    
    report += "💰 Статистика балансов:\n"
    report += f"  Пользователей с балансом: {users_with_balance}\n"
    report += f"  Общая сумма TPCoin: {total_balance:,}\n\n"
    
    report += "📝 Статистика логов:\n"
    report += f"  Логи пользователей: {logs_stats.get('user_logs', 0)}\n"
    report += f"  Логи администраторов: {logs_stats.get('admin_logs', 0)}\n"
    report += f"  Логи команд админов: {logs_stats.get('admin_command_logs', 0)}\n"
    report += f"  Системные логи: {logs_stats.get('system_logs', 0)}\n"
    report += f"  Логи ошибок: {logs_stats.get('error_logs', 0)}\n"
    report += f"  Логи переводов: {logs_stats.get('transfer_logs', 0)}\n"
    
    await message.answer(report)


# Обработка всех остальных сообщений
@dp.message()
async def handle_message(message: Message, state: FSMContext):
    """Обработка всех остальных сообщений"""
    if not await check_ban_middleware(message):
        return
    
    # Проверяем, есть ли активное состояние FSM (для поддержки)
    current_state = await state.get_state()
    if current_state:
        # Если есть активное состояние, пропускаем обработку здесь
        # Сообщение будет обработано соответствующим обработчиком состояния
        return
    
    # Проверяем, является ли сообщение командой (начинается с /)
    if message.text and message.text.startswith("/"):
        # Это неизвестная команда
        log_user_action(message.from_user, f"Неизвестная команда: {message.text[:50]}")
        await message.answer(
            "❓ Неизвестная команда.\n\n"
            "Используйте /help для просмотра доступных команд."
        )
        return
    
    # Обычное сообщение (не команда)
    log_user_action(message.from_user, f"Сообщение: {message.text[:50] if message.text else 'Медиа'}")


# ========== ОБРАБОТКА ВРЕМЕННЫХ БАНОВ ==========

async def process_expired_temp_bans():
    """Обрабатывает истекшие временные баны"""
    try:
        expired_user_ids = remove_expired_temp_bans()
        
        for user_id in expired_user_ids:
            # Разбаниваем пользователя, если он еще забанен
            if is_banned(user_id):
                # Создаем объект для unban_user (нужен только для логирования)
                class FakeAdmin:
                    def __init__(self):
                        self.id = CREATOR_ID
                
                fake_admin = FakeAdmin()
                unban_user(fake_admin, str(user_id))
                
                # Отправляем уведомление пользователю
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text="✅ Ваш временный бан истек. Доступ восстановлен."
                    )
                except Exception as e:
                    log_error("TEMP_BAN_UNBAN", f"Ошибка отправки уведомления пользователю {user_id}", str(e))
                
                log_system_event("SYSTEM", f"Автоматический разбан пользователя {user_id}")
    except Exception as e:
        log_error("TEMP_BAN_PROCESS", "Ошибка обработки истекших временных банов", str(e))


async def temp_ban_checker():
    """Периодическая проверка временных банов"""
    while True:
        try:
            await process_expired_temp_bans()
            # Проверяем каждые 5 минут
            await asyncio.sleep(300)
        except Exception as e:
            log_error("TEMP_BAN_CHECKER", "Ошибка в периодической проверке временных банов", str(e))
            await asyncio.sleep(300)


# ========== ГЛАВНАЯ ФУНКЦИЯ ==========
async def main():
    """Главная функция запуска бота"""
    try:
        log_system_event("SYSTEM", "Бот запущен")
        print("Бот запущен...")
        
        # Обрабатываем истекшие временные баны при запуске
        await process_expired_temp_bans()
        
        # Запускаем периодическую проверку временных банов
        asyncio.create_task(temp_ban_checker())
        
        await dp.start_polling(bot)
    except Exception as e:
        log_error("MAIN", "Критическая ошибка при запуске бота", str(e))
        print(f"Критическая ошибка: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
