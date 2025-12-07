# Telegram Bot on aiogram 3

Telegram bot with access control system, logging, user management, TPCoin virtual currency, achievements system, and optional TON Connect integration.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `config.json` file in the project root with the following structure:
```json
{
  "BOT_TOKEN": "your_bot_token",
  "CREATOR_ID": 123456789
}
```

   To get a bot token:
   - Find [@BotFather](https://t.me/BotFather) in Telegram
   - Send `/newbot` command
   - Follow the instructions
   - Copy the received token to `BOT_TOKEN` in `config.json`

   To find your Telegram ID:
   - Find [@userinfobot](https://t.me/userinfobot) in Telegram
   - Send `/start` command
   - Copy your ID to `CREATOR_ID` in `config.json`

## Running

```bash
python bot.py
```

## Data Storage

The bot uses **SQLite database** (`bot_database.db`) for data storage. All user data, balances, achievements, logs, and administrative information are stored in the database.

### Database Structure:
- `users` - all bot users
- `admins` - administrators list
- `blacklist` - blocked users
- `achievements` - list of all achievements
- `user_achievements` - user achievements
- `balances` - user TPCoin balances
- `temp_bans` - temporary bans
- `user_logs` - user action logs
- `admin_logs` - administrator action logs
- `admin_command_logs` - administrator command logs
- `system_logs` - system logs
- `error_logs` - error logs
- `transfer_logs` - TPCoin transfer logs

**Note:** The project was migrated from `.txt` files to SQLite. See `MIGRATION_README.md` for migration details.

## Commands

### For all users:
- `/start` - start the bot
- `/profile` - user profile
- `/balance` - TPCoin balance
- `/transfer amount id` - transfer TPCoin to another user
- `/myach` - list of achievements
- `/contact` - contact support
- `/tonconnect` - connect TON wallet (optional, requires TON Connect manifest)
- `/tonconnect_disconnect` - disconnect TON wallet (optional)
- `/help` - list of available commands

### For administrators and creator:
- `/ban id` - block a user
- `/unban id` - unblock a user
- `/tempban id hours reason` - temporary ban
- `/massban id1 id2 ...` - mass ban users
- `/banlist` - list of banned users
- `/achlist` - list of all achievements
- `/sendach achievementID userID` - grant achievement
- `/removeach achievementID userID` - remove achievement from user
- `/masssendach achievementID` - mass grant achievement
- `/addbalance amount id` - add balance to user
- `/removebalance amount id` - remove balance from user
- `/topbalance` - top users by balance
- `/sendsms text` - broadcast message to all users
- `/sendprivat text --id123456789` - send message to one user
- `/search id` - user information
- `/userlogs` - last 20 lines of user logs
- `/errorlogs` - last 20 lines of error logs
- `/ping` - bot response time

### Creator only:
- `/addadmin id` - assign administrator
- `/unadmin id` - remove administrator
- `/adminlist` - list of all administrators
- `/sendcoin amount id` - transfer TPCoin
- `/masssendcoin amount` - mass send TPCoin to all users
- `/newach id name` - create new achievement
- `/deleteach achievementID` - delete achievement from system
- `/adminlogs` - administrator logs
- `/systemlogs` - system logs
- `/test` - system statistics

## Features

- **Access Control System**: Three-level access (Creator, Admin, User)
- **Logging System**: Separate logs for users, admins, system events, and errors
- **User Management**: User registration, blocking/unblocking, temporary bans
- **Achievement System**: Create, grant, and manage achievements for users
- **Balance System**: TPCoin virtual currency with transfers between users
- **Support System**: User support with FSM states for communication
- **Broadcast System**: Send messages to all users or specific users
- **TON Connect Integration**: Optional TON wallet connection (requires accessible manifest)
- **Statistics**: System statistics and monitoring
- **SQLite Database**: Reliable data storage with automatic migration

## TON Connect (Optional)

The bot includes optional TON Connect integration for connecting TON wallets. If the TON Connect manifest is unavailable, the bot will start normally but TON-related commands (`/tonconnect`, `/tonconnect_disconnect`) will be disabled.

The manifest URL is configured in `bot.py` (default: GitHub repository). If you want to use TON Connect:
1. Ensure the manifest is accessible at the configured URL
2. The bot will automatically enable TON Connect features if the manifest is available
3. If the manifest is unavailable, the bot will continue working without TON features

## License

This project is open source and available for use.
