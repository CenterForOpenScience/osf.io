import os
from website import settings


def get_path(page_name, id=None, category=None):
    """
    Checks the path by adding file_name at the end
    :param page_name: pages that belong to each category.
    :param id: uid, pid o nid
    :param category: node or user
    :param file_name: Unique file name
    :return: if path exists, returns none else return path

    """

    if page_name == 'index':
        path = os.path.join(settings.SEO_CACHE, page_name)
    else:
        path = os.path.join(settings.SEO_CACHE, category, id, page_name)

    return {
        'path': path.replace(page_name, '', 1),
        'full_path': path + '.html'
    }
