from .common import *
from .users import *

from website import settings

def _get_or_create_category(category_name, color):
    match = [c['id'] for c in _categories if c['slug'] == category_name]
    if len(match) > 0:
        return match[0]
    return create_category(category_name, color)

def get_categories():
    result = request('get', '/categories.json')
    return result['category_list']['categories']

def create_category(category_name, color):
    data = {}
    data['name'] = category_name
    data['slug'] = category_name
    data['color'] = color
    data['text_color'] = 'FFFFFF'
    data['allow_badges'] = 'true'
    #data['permissions[everyone]'] = '2'
    return request('post', '/categories', data)['category']['id']

_categories = get_categories()

file_category = _get_or_create_category('Files', settings.DISCOURSE_CATEGORY_COLORS[0])
wiki_category = _get_or_create_category('Wikis', settings.DISCOURSE_CATEGORY_COLORS[1])
project_category = _get_or_create_category('Projects', settings.DISCOURSE_CATEGORY_COLORS[2])
