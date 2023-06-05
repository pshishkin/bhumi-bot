import os
from decimal import Decimal

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

# drop settings
SNAPSHOTS_DIR = os.getenv('SNAPSHOTS_DIR', './data/snapshots/')
SOL_DROP_AMOUNT = Decimal(os.getenv('SOL_DROP_AMOUNT', '0.003'))
BHUMI_DROP_BASE = int(os.getenv('BHUMI_DROP_BASE', '13'))
SOLANA_PRIVATE_KEY = os.getenv('SOLANA_PRIVATE_KEY', '123')

# tg parser settings
TG_API_ID = os.getenv('TG_API_ID', '123')
TG_API_HASH = os.getenv('TG_API_HASH', '123')
TG_PHONE_NUMBER = os.getenv('TG_PHONE_NUMBER', '+123')

# discord bot
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '123')
DISCORD_INTRO_URL = os.getenv('DISCORD_INTRO_URL', 'https://discord.com/channels/1027527819854630994/1109091415444697178')
SOLANA_DAILY_STASH_KEY = os.getenv('SOLANA_DAILY_STASH_KEY', '123')
BHUMI_TO_ENTER = int(os.getenv('BHUMI_TO_ENTER', '130'))
E_WALLET_PUBKEY = os.getenv('E_WALLET_PUBKEY', '123')