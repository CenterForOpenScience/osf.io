# -*- coding: utf-8 -*-

import weakref
import werkzeug
import collections

from modularodm.cache import Cache
from modularodm.writequeue import WriteQueue


# Dictionary of proxies, keyed on base schema, class variable label, and
# extension-specific key (e.g. a Flask request). The final key uses a weak
# reference to avoid memory leaks.
proxies = collections.defaultdict(
    lambda: collections.defaultdict(weakref.WeakKeyDictionary)
)

# Class variables on ``StoredObject`` that should be request-local under
# concurrent use
proxied_members = {
    '_cache': Cache,
    '_object_cache': Cache,
    'queue': WriteQueue,
}


def proxy_factory(BaseSchema, label, ProxiedClass, get_key):
    """Create a proxy to a class instance stored in ``proxies``.

    :param class BaseSchema: Base schema (e.g. ``StoredObject``)
    :param str label: Name of class variable to set
    :param class ProxiedClass: Class to get or create
    :param function get_key: Extension-specific key function; may return e.g.
        the current Flask request

    """
    def local():
        key = get_key()
        try:
            return proxies[BaseSchema][label][key]
        except KeyError:
            proxies[BaseSchema][label][key] = ProxiedClass()
            return proxies[BaseSchema][label][key]
    return werkzeug.local.LocalProxy(local)


def with_proxies(proxy_map, get_key):
    """Class decorator factory; adds proxy class variables to target class.

    :param dict proxy_map: Mapping between class variable labels and proxied
        classes
    :param function get_key: Extension-specific key function; may return e.g.
        the current Flask request

    """
    def wrapper(cls):
        for label, ProxiedClass in proxy_map.iteritems():
            proxy = proxy_factory(cls, label, ProxiedClass, get_key)
            setattr(cls, label, proxy)
        return cls
    return wrapper
