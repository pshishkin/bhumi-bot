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
WEB_PASS = os.getenv('VIDEO_ROOT', 'a')

