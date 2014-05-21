"""
structures.py
~~~~~~~~~~~~~

Defines structures used by the httpcache module.
"""
from .compat import MutableMapping, OrderedDict


class RecentOrderedDict(MutableMapping):
    """
    A custom variant of the OrderedDict that ensures that the object most
    recently inserted or retrieved from the dictionary is at the top of the
    dictionary enumeration.
    """
    def __init__(self, *args, **kwargs):
        self._data = OrderedDict(*args, **kwargs)

    def __setitem__(self, key, value):
        if key in self._data:
            del self._data[key]
        self._data[key] = value

    def __getitem__(self, key):
        value = self._data[key]
        del self._data[key]
        self._data[key] = value
        return value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __contains__(self, value):
        return self._data.__contains__(value)

    def items(self):
        return self._data.items()

    def keys(self):
        return self._data.keys()
