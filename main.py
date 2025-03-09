import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application, MessageHandler, filters
import paramiko
import json

# Переменные окружения
TOKEN = os.getenv('TELEGRAM_TOKEN')
SFTP_HOST = os.getenv('SFTP_HOST')
SFTP_PORT = os.getenv('SFTP_PORT')
SFTP_USERNAME = os.getenv('SFTP_USER')
SFTP_PASSWORD = os.getenv('SFTP_PASSWORD')
WHITELIST_PATH = 'whitelist.json'

# Переменные окружения
TOKEN = os.getenv('TELEGRAM_TOKEN')
SFTP_HOST = 'solar.minerent.net'
SFTP_PORT = 2022
SFTP_USERNAME = 'maksimilari.dc4946dc'
SFTP_PASSWORD = os.getenv('SFTP_PASSWORD')
WHITELIST_PATH = 'whitelist.json'  # Уточните путь, если файл в подпапке

# Создаем приложение
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Отправь мне никнейм для добавления в вайтлист.')

def get_sftp_connection():
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USERNAME, password=SFTP_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    return sftp, transport

def add_to_whitelist(username):
    try:
        sftp, transport = get_sftp_connection()
        try:
            with sftp.open(WHITELIST_PATH, 'r') as f:
                whitelist = json.load(f)
        except:
            whitelist = []
        if not any(player['name'] == username for player in whitelist):
            new_entry = {'uuid': 'offline-player-uuid', 'name': username}
            whitelist.append(new_entry)
            with sftp.open(WHITELIST_PATH, 'w') as f:
                json.dump(whitelist, f, indent=4)
            sftp.close()
            transport.close()
            return True
        sftp.close()
        transport.close()
        return False
    except Exception as e:
        print(f"Ошибка SFTP: {e}")
        return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    if not username.isalnum() or len(username) > 16:
        await update.message.reply_text('Некорректный ник! Используй только буквы и цифры, максимум 16 символов.')
        return
    if add_to_whitelist(username):
        await update.message.reply_text(f'Ник {username} добавлен в вайтлист!')
    else:
        await update.message.reply_text(f'Ник {username} уже есть в вайтлисте или произошла ошибка.')

# Регистрация обработчиков
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Запуск вебхука
port = int(os.environ.get("PORT", 8443))
webhook_url = f"https://dulmine-bot.onrender.com/{TOKEN}"  # Замените на реальный URL после деплоя

# Эта часть запускается только если скрипт запущен напрямую (не через gunicorn)
if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=webhook_url
    )