"""
Скрипт миграции данных из .txt файлов в SQLite базу данных
"""
import os
import glob
from datetime import datetime
from database import (
    init_database,
    add_user,
    add_admin,
    ban_user,
    create_achievement,
    add_user_achievement,
    set_user_balance,
    add_temp_ban,
    log_user_action,
    log_admin_action,
    log_admin_command,
    log_system_event,
    log_error,
    log_transfer
)


def migrate_users():
    """Мигрирует пользователей из userlist.txt"""
    if not os.path.exists("userlist.txt"):
        print("Файл userlist.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("userlist.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(" | ")
            if len(parts) >= 4:
                user_id = int(parts[0])
                full_name = parts[1]
                username = parts[2]
                first_start = parts[3]
                add_user(user_id, full_name, username, first_start)
                count += 1
    
    print(f"✅ Мигрировано пользователей: {count}")
    return count


def migrate_admins():
    """Мигрирует администраторов из adminlist.txt"""
    if not os.path.exists("adminlist.txt"):
        print("Файл adminlist.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("adminlist.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(" | ")
            if len(parts) >= 4:
                admin_id = int(parts[0])
                full_name = parts[1]
                username = parts[2]
                added_date = parts[3]
                add_admin(admin_id, full_name, username, added_date)
                count += 1
    
    print(f"✅ Мигрировано администраторов: {count}")
    return count


def migrate_blacklist():
    """Мигрирует черный список из blacklist.txt"""
    if not os.path.exists("blacklist.txt"):
        print("Файл blacklist.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("blacklist.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(" | ")
            if len(parts) >= 4:
                user_id = int(parts[0])
                full_name = parts[1]
                username = parts[2]
                banned_date = parts[3]
                banned_by = parts[4] if len(parts) > 4 else "NA"
                ban_user(user_id, full_name, username, banned_date, banned_by)
                count += 1
    
    print(f"✅ Мигрировано забаненных пользователей: {count}")
    return count


def migrate_achievements():
    """Мигрирует достижения из achlist.txt"""
    if not os.path.exists("achlist.txt"):
        print("Файл achlist.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("achlist.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(" | ")
            if len(parts) >= 2:
                ach_id = parts[0]
                ach_name = parts[1]
                created = parts[2] if len(parts) > 2 else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                create_achievement(ach_id, ach_name, created)
                count += 1
    
    print(f"✅ Мигрировано достижений: {count}")
    return count


def migrate_user_achievements():
    """Мигрирует достижения пользователей из ach-user-list.txt"""
    if not os.path.exists("ach-user-list.txt"):
        print("Файл ach-user-list.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("ach-user-list.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(" | ")
            if len(parts) >= 6:
                user_id = int(parts[0])
                # parts[1] и parts[2] - имя и username (не нужны для таблицы)
                given_date = parts[3]
                given_by = parts[4]
                ach_id = parts[5]
                # parts[6] - название достижения (не нужно, берется из таблицы achievements)
                add_user_achievement(user_id, ach_id, given_date, given_by)
                count += 1
    
    print(f"✅ Мигрировано достижений пользователей: {count}")
    return count


def migrate_balances():
    """Мигрирует балансы из файлов balance_*.txt"""
    balance_files = glob.glob("balance_*.txt")
    if not balance_files:
        print("Файлы балансов не найдены, пропускаем...")
        return 0
    
    count = 0
    for balance_file in balance_files:
        try:
            # Извлекаем user_id из имени файла
            user_id_str = balance_file.replace("balance_", "").replace(".txt", "")
            user_id = int(user_id_str)
            
            with open(balance_file, "r", encoding="utf-8") as f:
                balance_str = f.read().strip()
                if balance_str:
                    balance = int(balance_str)
                    set_user_balance(user_id, balance)
                    count += 1
        except (ValueError, FileNotFoundError) as e:
            print(f"⚠️ Ошибка при миграции баланса из {balance_file}: {e}")
            continue
    
    print(f"✅ Мигрировано балансов: {count}")
    return count


def migrate_temp_bans():
    """Мигрирует временные баны из tempban.txt"""
    if not os.path.exists("tempban.txt"):
        print("Файл tempban.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("tempban.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(" | ")
            if len(parts) >= 4:
                user_id = int(parts[0])
                unban_time = parts[1]
                reason = parts[2]
                banned_by = int(parts[3])
                banned_at = parts[4] if len(parts) > 4 else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                add_temp_ban(user_id, unban_time, reason, banned_by, banned_at)
                count += 1
    
    print(f"✅ Мигрировано временных банов: {count}")
    return count


def migrate_user_logs():
    """Мигрирует логи пользователей из userlogs.txt"""
    if not os.path.exists("userlogs.txt"):
        print("Файл userlogs.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("userlogs.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(" | ")
            if len(parts) >= 5:
                user_id = int(parts[0])
                full_name = parts[1]
                username = parts[2]
                timestamp = parts[3]
                action = parts[4]
                log_user_action(user_id, full_name, username, timestamp, action)
                count += 1
    
    print(f"✅ Мигрировано логов пользователей: {count}")
    return count


def migrate_admin_logs():
    """Мигрирует логи администраторов из adminlogs.txt"""
    if not os.path.exists("adminlogs.txt"):
        print("Файл adminlogs.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("adminlogs.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(" | ")
            if len(parts) >= 5:
                user_id = int(parts[0])
                full_name = parts[1]
                username = parts[2]
                timestamp = parts[3]
                action = parts[4]
                log_admin_action(user_id, full_name, username, timestamp, action)
                count += 1
    
    print(f"✅ Мигрировано логов администраторов: {count}")
    return count


def migrate_admin_command_logs():
    """Мигрирует логи команд администраторов из admin-com-logs.txt"""
    if not os.path.exists("admin-com-logs.txt"):
        print("Файл admin-com-logs.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("admin-com-logs.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(" | ")
            if len(parts) >= 5:
                user_id = int(parts[0])
                full_name = parts[1]
                username = parts[2]
                timestamp = parts[3]
                command = parts[4]
                log_admin_command(user_id, full_name, username, timestamp, command)
                count += 1
    
    print(f"✅ Мигрировано логов команд администраторов: {count}")
    return count


def migrate_system_logs():
    """Мигрирует системные логи из systemlogs.txt"""
    if not os.path.exists("systemlogs.txt"):
        print("Файл systemlogs.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("systemlogs.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(" | ")
            if len(parts) >= 3:
                initiator = parts[0]
                timestamp = parts[1]
                action = parts[2]
                log_system_event(initiator, timestamp, action)
                count += 1
    
    print(f"✅ Мигрировано системных логов: {count}")
    return count


def migrate_error_logs():
    """Мигрирует логи ошибок из errorlogs.txt"""
    if not os.path.exists("errorlogs.txt"):
        print("Файл errorlogs.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("errorlogs.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(" | ")
            if len(parts) >= 3:
                error_type = parts[0]
                timestamp = parts[1]
                error_message = parts[2]
                context = parts[3] if len(parts) > 3 else ""
                log_error(error_type, timestamp, error_message, context)
                count += 1
    
    print(f"✅ Мигрировано логов ошибок: {count}")
    return count


def migrate_transfer_logs():
    """Мигрирует логи переводов из transferlogs.txt"""
    if not os.path.exists("transferlogs.txt"):
        print("Файл transferlogs.txt не найден, пропускаем...")
        return 0
    
    count = 0
    with open("transferlogs.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Формат: timestamp | from_user_id (from_name) -> to_user_id (to_name) | amount TPCoin
            # Пример: 2025-12-07 18:20:39 | 8333031050 (Викентий Пачковский) -> 7626194278 (Пачковский) | 100 TPCoin
            try:
                parts = line.split(" | ")
                if len(parts) >= 3:
                    timestamp = parts[0]
                    transfer_info = parts[1]
                    amount_info = parts[2]
                    
                    # Парсим информацию о переводе
                    if " -> " in transfer_info:
                        from_part, to_part = transfer_info.split(" -> ")
                        
                        # Извлекаем from_user_id
                        from_user_id = int(from_part.split(" (")[0])
                        from_name = from_part.split(" (")[1].rstrip(")")
                        
                        # Извлекаем to_user_id
                        to_user_id = int(to_part.split(" (")[0])
                        to_name = to_part.split(" (")[1].rstrip(")")
                        
                        # Извлекаем amount
                        amount = int(amount_info.split()[0])
                        
                        log_transfer(timestamp, from_user_id, to_user_id, amount, from_name, to_name)
                        count += 1
            except (ValueError, IndexError) as e:
                print(f"⚠️ Ошибка при парсинге строки лога перевода: {line[:50]}... - {e}")
                continue
    
    print(f"✅ Мигрировано логов переводов: {count}")
    return count


def main():
    """Главная функция миграции"""
    print("=" * 50)
    print("Начало миграции данных из .txt файлов в SQLite")
    print("=" * 50)
    
    # Инициализируем базу данных
    print("\n📦 Инициализация базы данных...")
    init_database()
    print("✅ База данных инициализирована")
    
    # Мигрируем данные
    print("\n📥 Начало миграции данных...\n")
    
    total = 0
    total += migrate_users()
    total += migrate_admins()
    total += migrate_blacklist()
    total += migrate_achievements()
    total += migrate_user_achievements()
    total += migrate_balances()
    total += migrate_temp_bans()
    total += migrate_user_logs()
    total += migrate_admin_logs()
    total += migrate_admin_command_logs()
    total += migrate_system_logs()
    total += migrate_error_logs()
    total += migrate_transfer_logs()
    
    print("\n" + "=" * 50)
    print(f"✅ Миграция завершена! Всего записей мигрировано: {total}")
    print("=" * 50)
    print("\n💡 Теперь можно обновить bot.py для использования SQLite")
    print("💡 Старые .txt файлы можно сохранить как резервную копию")


if __name__ == "__main__":
    main()
