import os

MONGO_CONN_STR = os.getenv('MONGO_CONN_STR', 'mongodb://localhost:27017')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'Tokennnnn')
MONGO_DATABASE = os.getenv('MONGO_DATABASE', 'development')
TRAIN_USER_ID = int(os.getenv('TRAIN_USER_ID', '11'))
