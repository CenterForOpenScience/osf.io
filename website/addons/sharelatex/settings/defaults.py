import os

from website.settings import parent_dir


HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(parent_dir(HERE), 'static')

MAX_RENDER_SIZE = (1024 ** 2) * 3

ALLOWED_ORIGIN = '*'

SHARELATEX_URL = 'http://localhost:3000'
