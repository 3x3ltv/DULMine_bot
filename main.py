import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import paramiko
import json

# Переменные окружения
TOKEN = os.getenv('TELEGRAM_TOKEN')
SFTP_HOST = os.getenv('SFTP_HOST')
SFTP_PORT = int(os.getenv('SFTP_PORT', '2022'))
SFTP_USERNAME = os.getenv('SFTP_USER')
SFTP_PASSWORD = os.getenv('SFTP_PASSWORD')
WHITELIST_PATH = 'whitelist.json'

# Создаем приложение
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Отправь мне никнейм для добавления в вайтлист.')

def get_sftp_connection():
    try:
        print(f"Connecting to SFTP: {SFTP_HOST}:{SFTP_PORT} with user {SFTP_USERNAME}")
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USERNAME, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        print("SFTP connection established")
        return sftp, transport
    except Exception as e:
        print(f"SFTP connection failed: {e}")
        raise

def add_to_whitelist(username):
    try:
        sftp, transport = get_sftp_connection()
        try:
            print(f"Reading {WHITELIST_PATH}")
            with sftp.open(WHITELIST_PATH, 'r') as f:
                whitelist = json.load(f)
            print(f"Current whitelist: {whitelist}")
        except Exception as e:
            print(f"File not found or error reading {WHITELIST_PATH}: {e}")
            whitelist = []
            print("Starting with empty whitelist")

        if not any(player.get('name') == username for player in whitelist):
            new_entry = {'uuid': 'offline-player-uuid', 'name': username}
            whitelist.append(new_entry)
            print(f"Adding {username} to whitelist: {whitelist}")
            with sftp.open(WHITELIST_PATH, 'w') as f:
                json.dump(whitelist, f, indent=4)
            print(f"Successfully wrote to {WHITELIST_PATH}")
            sftp.close()
            transport.close()
            return True
        else:
            print(f"Username {username} already in whitelist")
            sftp.close()
            transport.close()
            return False
    except Exception as e:
        print(f"Ошибка SFTP: {e}")
        return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    # Проверяем, что ник состоит только из букв, цифр и _, и не длиннее 16 символов
    if not all(c.isalnum() or c == '_' for c in username) or len(username) > 16:
        await update.message.reply_text('Некорректный ник! Используй только буквы, цифры и подчеркивание, максимум 16 символов.')
        return
    if add_to_whitelist(username):
        await update.message.reply_text(f'Ник {username} добавлен в вайтлист!')
    else:
        await update.message.reply_text(f'Ник {username} уже есть в вайтлисте или произошла ошибка.')

# Регистрация обработчиков
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Запуск приложения
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8443))  # Render предоставляет порт через $PORT
    webhook_url = f"https://dulmine-bot.onrender.com/{TOKEN}"
    print(f"Starting webhook on port {port} with URL {webhook_url}")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=webhook_url
    )