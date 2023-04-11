import os

# common settings
MONGO_CONN_STR = os.getenv('MONGO_CONN_STR', 'mongodb://localhost:27017')
MONGO_DATABASE = os.getenv('MONGO_DATABASE', 'development')

# telegram settings
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'Tokennnnn')
TRAIN_USER_ID = int(os.getenv('TRAIN_USER_ID', '11'))

# web settings
VIDEO_ROOT = os.getenv('VIDEO_ROOT', './videos')
WEB_USERNAME = os.getenv('WEB_USERNAME', 'a')
WEB_PASS = os.getenv('WEB_PASS', 'aa')
COOKIE_SECRET = "your_cookie_secret"

# tg parser settings
TG_API_ID = os.getenv('TG_API_ID', '123')
TG_API_HASH = os.getenv('TG_API_HASH', '123')
TG_PHONE_NUMBER = os.getenv('TG_PHONE_NUMBER', '+123')

# discord bot
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '123')
SOLANA_PRIVATE_KEY=os.getenv('SOLANA_PRIVATE_KEY', '123')