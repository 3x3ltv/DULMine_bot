import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import paramiko
import json
import requests

TOKEN = os.getenv('TELEGRAM_TOKEN')
SFTP_HOST = os.getenv('SFTP_HOST')
SFTP_PORT = int(os.getenv('SFTP_PORT'))
SFTP_USERNAME = os.getenv('SFTP_USER')
SFTP_PASSWORD = os.getenv('SFTP_PASSWORD')
WHITELIST_PATH = 'whitelist.json'

application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Отправь мне никнейм для добавления в вайтлист.')

def get_uuid(username):
    try:
        print(f"Fetching UUID for username: {username}")
        api_url = f"https://playerdb.co/api/player/minecraft/{requests.utils.quote(username)}"
        print(f"Requesting PlayerDB API URL: {api_url}")
        api_response = requests.get(api_url, timeout=10)
        api_response.raise_for_status()
        data = api_response.json()
        print(f"PlayerDB API response: {data}")
        if data.get('success') and data['data'].get('player'):
            uuid = data['data']['player'].get('id')
            if uuid:
                print(f"Found UUID from PlayerDB API: {uuid}")
                return uuid
            else:
                print("No UUID found in PlayerDB response")
        else:
            print(f"PlayerDB API error: {data.get('error', 'Unknown error')}")
        return None
    except requests.RequestException as e:
        print(f"Network error fetching UUID: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching UUID: {e}")
        return None

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

def add_to_whitelist(username, uuid):
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
            new_entry = {'uuid': uuid, 'name': username}
            whitelist.append(new_entry)
            print(f"Adding {username} with UUID {uuid} to whitelist: {whitelist}")
            with sftp.open(WHITELIST_PATH, 'w') as f:
                json_data = json.dumps(whitelist, indent=4)
                f.write(json_data)
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
    if not all(c.isalnum() or c == '_' for c in username) or len(username) > 16:
        await update.message.reply_text('Некорректный ник! Используй только буквы, цифры и подчеркивание, максимум 16 символов.')
        return

    uuid = get_uuid(username)
    if not uuid:
        await update.message.reply_text(f'Не удалось получить UUID для ника {username}. Возможно, ник неверный или сервер недоступен. Проверьте логи.')
        return

    if add_to_whitelist(username, uuid):
        await update.message.reply_text(f'Ник {username} с UUID {uuid} добавлен в вайтлист!')
    else:
        await update.message.reply_text(f'Ник {username} уже есть в вайтлисте или произошла ошибка.')

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Запуск приложения
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8443))
    webhook_url = f"https://dulmine-bot.onrender.com/{TOKEN}"
    print(f"Starting webhook on port {port} with URL {webhook_url}")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=webhook_url
    )