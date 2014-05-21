# -*- coding utf-8 -*-

import os
import copy

from .base import Storage, KeyExistsException
from ..query.queryset import BaseQuerySet
from ..query.query import QueryGroup
from ..query.query import RawQuery

from modularodm.utils import DirtyField
from modularodm.exceptions import MultipleResultsFound, NoResultsFound

try:
    import cpickle as pickle
except ImportError:
    import pickle


def _eq(data, test):
    if isinstance(data, list):
        return test in data
    return data == test

operators = {

    'eq':   _eq,

    'ne':   lambda data, test: data != test,
    'gt':   lambda data, test: data > test,
    'gte':  lambda data, test: data >= test,
    'lt':   lambda data, test: data < test,
    'lte':  lambda data, test: data <= test,
    'in':   lambda data, test: data in test,
    'nin':  lambda data, test: data not in test,

    'startswith':  lambda data, test: data.startswith(test),
    'endswith':    lambda data, test: data.endswith(test),
    'contains':    lambda data, test: test in data,
    'icontains':   lambda data, test: test.lower() in data.lower(),

}


class PickleQuerySet(BaseQuerySet):

    _sort = DirtyField(None)
    _offset = DirtyField(None)
    _limit = DirtyField(None)

    def __init__(self, schema, data):

        super(PickleQuerySet, self).__init__(schema)

        self._data = list(data)
        self._dirty = True

        self.data = []

    def _eval(self):

        if self._dirty:

            self.data = self._data[:]

            if self._sort is not None:

                for key in self._sort[::-1]:

                    if key.startswith('-'):
                        reverse = True
                        key = key.lstrip('-')
                    else:
                        reverse = False

                    self.data = sorted(
                        self.data,
                        key=lambda record: record[key],
                        reverse=reverse
                    )

            if self._offset is not None:
                self.data = self.data[self._offset:]

            if self._limit is not None:
                self.data = self.data[:self._limit]

            self._dirty = False

        return self

    def __getitem__(self, index, raw=False):
        super(PickleQuerySet, self).__getitem__(index)
        self._eval()
        key = self.data[index][self.primary]
        if raw:
            return key
        return self.schema.load(key)

    def __iter__(self, raw=False):
        self._eval()
        keys = [obj[self.primary] for obj in self.data]
        if raw:
            return keys
        return (self.schema.load(key) for key in keys)

    def __len__(self):
        self._eval()
        return len(self.data)

    count = __len__

    def get_key(self, index):
        return self.__getitem__(index, raw=True)

    def get_keys(self):
        return list(self.__iter__(raw=True))

    def sort(self, *keys):
        """ Iteratively sort data by keys in reverse order. """
        self._sort = keys
        return self

    def offset(self, n):
        self._offset = n
        return self

    def limit(self, n):
        self._limit = n
        return self


class PickleStorage(Storage):
    """ Storage backend using pickle. """

    QuerySet = PickleQuerySet

    def __init__(self, collection_name,  prefix='db_', ext='pkl'):
        """Build pickle file name and load data if exists.

        :param collection_name: Collection name
        :param prefix: File prefix.
        :param ext: File extension.

        """
        # Build filename
        filename = collection_name + '.' + ext
        if prefix:
            self.filename = prefix + filename
        else:
            self.filename = filename

        # Initialize empty store
        self.store = {}

        # Load file if exists
        if os.path.exists(self.filename):
            with open(self.filename, 'rb') as fp:
                data = fp.read()
                self.store = pickle.loads(data)

    def _delete_file(self):
        try:
            os.remove(self.filename)
        except OSError:
            pass

    def insert(self, primary_name, key, value):
        """Add key-value pair to storage. Key must not exist.

        :param key: Key
        :param value: Value

        """
        if key not in self.store:
            self.store[key] = value
            self.flush()
        else:
            msg = 'Key ({key}) already exists'.format(key=key)
            raise KeyExistsException(msg)

    def update(self, query, data):
        for pk in self.find(query, by_pk=True):
            for key, value in data.items():
                self.store[pk][key] = value

    def get(self, primary_name, key):
        data = self.store.get(key)
        if data is not None:
            return copy.deepcopy(data)

    def _remove_by_pk(self, key, flush=True):
        """Retrieve value from store.

        :param key: Key

        """
        try:
            del self.store[key]
        except Exception as error:
            pass
        if flush:
            self.flush()

    def remove(self, query=None):
        for key in self.find(query, by_pk=True):
            self._remove_by_pk(key, flush=False)
        self.flush()

    def flush(self):
        """ Save store to file. """
        with open(self.filename, 'wb') as fp:
            pickle.dump(self.store, fp, -1)

    def find_one(self, query=None, **kwargs):
        results = list(self.find(query))
        if len(results) == 1:
            return results[0]
        elif len(results) == 0:
            raise NoResultsFound()
        else:
            raise MultipleResultsFound(
                'Query for find_one must return exactly one result; '
                'returned {0}'.format(len(results))
            )

    def _match(self, value, query):

        if isinstance(query, QueryGroup):

            matches = [self._match(value, node) for node in query.nodes]

            if query.operator == 'and':
                return all(matches)
            elif query.operator == 'or':
                return any(matches)
            elif query.operator == 'not':
                return not any(matches)
            else:
                raise ValueError('QueryGroup operator must be <and>, <or>, or <not>.')

        elif isinstance(query, RawQuery):
            attribute, operator, argument = \
                query.attribute, query.operator, query.argument

            return operators[operator](value[attribute], argument)

        else:
            raise TypeError('Query must be a QueryGroup or Query object.')

    def find(self, query=None, **kwargs):
        """
        Return generator over query results. Takes optional
        by_pk keyword argument; if true, return keys rather than
        values.

        """
        if query is None:
            for key, value in self.store.iteritems():
                yield value
        else:
            for key, value in self.store.items():
                if self._match(value, query):
                    if kwargs.get('by_pk'):
                        yield key
                    else:
                        yield value

    def __repr__(self):
        return str(self.store)
