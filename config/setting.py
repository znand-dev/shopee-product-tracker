import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'your_bot_token_here')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'your_chat_id_here')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))  # 5 menit default

# Print untuk debugging (opsional)
print(f"Config loaded - Token: {TELEGRAM_BOT_TOKEN}, Chat ID: {TELEGRAM_CHAT_ID}, Interval: {CHECK_INTERVAL}")
