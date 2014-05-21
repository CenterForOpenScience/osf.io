import six
import time
import random
import itertools
from functools import wraps

from ..translators import DefaultTranslator


class KeyExistsException(Exception):
    pass


class Logger(object):

    def __init__(self):

        self.listening = False
        self.events = []
        self.xtra = []

    def listen(self, xtra=None):

        self.xtra.append(xtra)

        if self.listening:
            return False

        self.listening = True
        self.events = []
        return True

    def record_event(self, event):

        if self.listening:
            self.events.append(event)

    def report(self, sort_func=None):

        out = {}

        if sort_func is None:
            sort_func = lambda e: e.func.__name__

        heard = sorted(self.events, key=sort_func)

        for key, group in itertools.groupby(heard, sort_func):
            group = list(group)
            num_events = len(group)
            total_time = sum([event.elapsed_time for event in group])
            out[key] = (num_events, total_time)

        return out

    def pop(self):

        self.xtra.pop()

    def clear(self):

        self.listening = False
        self.events = []


class LogEvent(object):

    def __init__(self, func, start_time, stop_time, xtra=None):

        self.func = func
        self.start_time = start_time
        self.stop_time = stop_time
        self.elapsed_time = stop_time - start_time
        self.xtra = xtra

    def __repr__(self):

        return 'LogEvent("{func}", {start_time}, {stop_time}, {xtra})'.format(
            **self.__dict__
        )


def logify(func):

    @wraps(func)
    def wrapped(this, *args, **kwargs):

        # Note: Copy value of `this.logger.listening` here in the event that
        # this value is changed externally during the decorated function call.
        # TODO: Verify that this produces valid output for concurrent requests
        listening = this.logger.listening

        if listening:
            start_time = time.time()

        out = func(this, *args, **kwargs)

        if listening:
            stop_time = time.time()
            xtra = this.logger.xtra[-1]
            this.logger.record_event(
                LogEvent(
                    func,
                    start_time,
                    stop_time,
                    xtra
                )
            )

        return out

    return wrapped


class StorageMeta(type):

    def __new__(mcs, name, bases, dct):

        # Decorate methods
        for key, value in dct.items():
            if hasattr(value, '__call__') \
                    and not isinstance(value, type) \
                    and not key.startswith('_'):
                dct[key] = logify(value)

        # Run super-metaclass __new__
        return super(StorageMeta, mcs).__new__(mcs, name, bases, dct)


@six.add_metaclass(StorageMeta)
class Storage(object):
    """Abstract base class for storage objects. Subclasses (e.g. PickleStorage,
    MongoStorage, etc.) must define insert, update, get, remove, flush, and
    find_all methods.

    """

    translator = DefaultTranslator()
    logger = Logger()

    def _ensure_index(self, key):
        pass

    # todo allow custom id generator
    # todo increment n on repeated failures
    def _generate_random_id(self, n=5):
        """Generated random alphanumeric key.

        :param n: Number of characters in random key

        """
        alphabet = '23456789abcdefghijkmnpqrstuvwxyz'
        return ''.join(random.sample(alphabet, n))

    def _optimistic_insert(self, primary_name, value, n=5):
        """Attempt to insert with randomly generated key until insert
        is successful.

        :param str primary_name: The name of the primary key.
        :param dict value: The dictionary representation of the record.
        :param n: Number of characters in random key

        """
        while True:
            try:
                key = self._generate_random_id(n)
                value[primary_name] = key
                self.insert(primary_name, key, value)
            except KeyExistsException:
                pass
            break
        return key

    def insert(self, primary_name, key, value):
        '''Insert a new record.

        :param str primary_name: Name of primary key
        :param key: The value of the primary key
        :param dict value: The dictionary of attribute:value pairs
        '''
        raise NotImplementedError

    def update(self, query, data):
        """Update multiple records with new data.

        :param query: A query object.
        :param dict data: Dictionary of key:value pairs.
        """
        raise NotImplementedError

    def get(self, primary_name, key):
        """Get a single record.

        :param str primary_name: The name of the primary key.
        :param key: The value of the primary key.
        """
        raise NotImplementedError

    def remove(self, query=None):
        """Remove records.
        """
        raise NotImplementedError

    def flush(self):
        """Flush the database."""
        raise NotImplementedError

    def find_one(self, query=None, **kwargs):
        """Find a single record that matches ``query``.
        """
        raise NotImplementedError

    def find(self, query=None, **kwargs):
        """Query the database and return a query set.
        """
        raise NotImplementedError
