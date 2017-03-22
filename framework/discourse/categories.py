import logging

import requests

from framework.discourse import common
import framework.logging  # noqa importing this configures the logger, which would not otherwise be configured yet
from website import settings

logger = logging.getLogger(__name__)

file_category = None
wiki_category = None
project_category = None

def _get_or_create_category(categories, category_name):
    """Get category ID for the category name, creating the category if necessary

    :param string category_name: Name of category to return ID of
    :return int: category ID
    """
    match = [c['id'] for c in categories if c['slug'].lower() == category_name.lower()]
    if len(match) > 0:
        return match[0]
    return _create_category(category_name)

def _create_category(category_name):
    """Create category on Discourse and return category ID

    :param str category_name: Name to give the category
    :return int: category ID
    """
    data = {
        'name': category_name,
        'slug': category_name.lower(),
        'color': settings.DISCOURSE_CATEGORY_COLORS[category_name],
        'text_color': 'FFFFFF',
        'allow_badges': 'true'
    }
    return common.request('post', '/categories', data)['category']['id']

def load_basic_categories():
    """Attempts to load (or create) category ids from Discourse for the file, wiki, and project categories.
    They are left as None if it fails.
    """
    global file_category, wiki_category, project_category
    try:
        categories = common.request('get', '/categories.json')['category_list']['categories']

        file_category = _get_or_create_category(categories, 'Files')
        wiki_category = _get_or_create_category(categories, 'Wikis')
        project_category = _get_or_create_category(categories, 'Projects')
    except (common.DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Discourse is either not running, or is malfunctioning. For correct Discourse functionality, please configure Discourse and make sure it is running.')

load_basic_categories()
