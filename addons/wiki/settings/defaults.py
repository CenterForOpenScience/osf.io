import datetime
import os
import pytz

from website import settings

SHAREJS_HOST = 'localhost'
SHAREJS_PORT = 7007
SHAREJS_URL = f'{SHAREJS_HOST}:{SHAREJS_PORT}'

SHAREJS_DB_NAME = 'sharejs'
SHAREJS_DB_URL = os.environ.get('SHAREJS_DB_URL', f'mongodb://{settings.DB_HOST}:{settings.DB_PORT}/{SHAREJS_DB_NAME}')

# TODO: Change to release date for wiki change
WIKI_CHANGE_DATE = datetime.datetime.fromtimestamp(1423760098, pytz.utc)
