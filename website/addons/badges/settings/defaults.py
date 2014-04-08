import os

from website.settings import BASE_PATH


BADGES_LOCATION = '/static/img/badges'
BADGES_ABS_LOCATION = os.path.join(BASE_PATH, 'static/img/badges')

# 2mb in bytes
MAX_IMAGE_SIZE = 4 * 1024 ** 2
