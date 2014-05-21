# -*- coding: utf-8 -*-

def set_nested(data, value, *keys):
    """Assign to a nested dictionary.

    :param dict data: Dictionary to mutate
    :param value: Value to set
    :param list *keys: List of nested keys

    >>> data = {}
    >>> set_nested(data, 'hi', 'k0', 'k1', 'k2')
    >>> data
    {'k0': {'k1': {'k2': 'hi'}}}

    """
    if len(keys) == 1:
        data[keys[0]] = value
    else:
        if keys[0] not in data:
            data[keys[0]] = {}
        set_nested(data[keys[0]], value, *keys[1:])


class Cache(object):
    """Simple container for storing cached data.

    """
    def __init__(self):
        self.data = {}

    @property
    def raw(self):
        return self.data

    def set(self, schema, key, value):
        set_nested(self.data, value, schema, key)

    def get(self, schema, key):
        try:
            return self.data[schema][key]
        except KeyError:
            return None

    def pop(self, schema, key):
        self.data[schema].pop(key, None)

    def clear(self):
        self.__init__()

    def clear_schema(self, schema):
        self.data.pop(schema, None)

    def __nonzero__(self):
        return bool(self.data)
