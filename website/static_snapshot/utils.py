import os
from website import settings


def check_path(page_name, id=None, category=None, file_name=None):


    if page_name == 'index':
        path = os.path.join(settings.SEO_CACHE, page_name, file_name)
    else:
        path = os.path.join(settings.SEO_CACHE, category, id, page_name, file_name)

    if os.path.exists(path):
        return ''
    else:
        return path.replace(file_name, '', 1)
