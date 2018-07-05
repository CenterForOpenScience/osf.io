import os
from werkzeug.local import LocalProxy
from django.utils.module_loading import import_string

from website import settings

__all__ = ('search', 'driver', 'build_driver', '_set_driver')

def build_driver(name):
    if name not in settings.SEARCH_ENGINES:
        raise Exception('Search Engine "{}" is not configured'.format(name))
    return import_string(settings.SEARCH_ENGINES[name]['DRIVER'])(
        *settings.SEARCH_ENGINES[name]['ARGS'],
        **settings.SEARCH_ENGINES[name]['KWARGS']
    )

_driver = build_driver(os.environ.get('SEARCH_ENGINE', 'default'))

def _get_driver():
    return _driver

def _set_driver(driver):
    global _driver
    _driver = driver

search = driver = LocalProxy(_get_driver)
