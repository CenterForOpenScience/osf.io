from .common import DiscourseException, request

import requests
import logging
import framework.logging # importing this configures the logger
from website import settings

logger = logging.getLogger(__name__)

_categories = None

file_category = None
wiki_category = None
project_category = None

def _get_or_create_category(category_name, color):
    """Get category ID for the category name, creating the category if necessary

    :param string category_name: Name of category to return ID of
    :param string color: 6-digit hexadecimal color of category if it needs to be created
    :return int: category ID
    """
    match = [c['id'] for c in _categories if c['slug'].lower() == category_name.lower()]
    if len(match) > 0:
        return match[0]
    return _create_category(category_name, color)

def _get_categories():
    """Return list of categories on Discourse with their attributes
    :return list: list of categories as dictionaries
    """
    result = request('get', '/categories.json')
    return result['category_list']['categories']

def _create_category(category_name, color):
    """Create category on Discourse and return category ID

    :param str category_name: Name to give the category
    :param str color: 6-digit hexadecimal color
    :return int: category ID
    """
    data = {}
    data['name'] = category_name
    data['slug'] = category_name.lower()
    data['color'] = color
    data['text_color'] = 'FFFFFF'
    data['allow_badges'] = 'true'
    #data['permissions[everyone]'] = '2'
    return request('post', '/categories', data)['category']['id']


def load_basic_categories():
    """Attempts to load (or create) category ids from Discourse for the file, wiki, and project categories.
    They are left as None if it fails.
    """
    global _categories, file_category, wiki_category, project_category
    try:
        _categories = _get_categories()

        file_category = _get_or_create_category('Files', settings.DISCOURSE_CATEGORY_COLORS[0])
        wiki_category = _get_or_create_category('Wikis', settings.DISCOURSE_CATEGORY_COLORS[1])
        project_category = _get_or_create_category('Projects', settings.DISCOURSE_CATEGORY_COLORS[2])
    except (DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Discourse is either not running, or is malfunctioning. For correct Discourse functionality, please configure Discourse and make sure it is running.')

load_basic_categories()
