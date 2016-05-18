# -*- coding: utf-8 -*-
import functools
import httplib as http
import re

import markupsafe
import pymongo
from modularodm import Q
from modularodm.query import QueryBase
from modularodm.exceptions import ValidationValueError, NoResultsFound, MultipleResultsFound

from framework.exceptions import HTTPError

# MongoDB forbids field names that begin with "$" or contain ".". These
# utilities map to and from Mongo field names.

mongo_map = {
    '.': '__!dot!__',
    '$': '__!dollar!__',
}


def to_mongo(item):
    for key, value in mongo_map.items():
        item = item.replace(key, value)
    return item


def to_mongo_key(item):
    return to_mongo(item).strip().lower()


def from_mongo(item):
    for key, value in mongo_map.items():
        item = item.replace(value, key)
    return item


sanitize_pattern = re.compile(r'<\/?[^>]+>')
def sanitized(value):
    if value != sanitize_pattern.sub('', value):
        raise ValidationValueError('Unsanitary string')


def unique_on(*groups):
    """Decorator for subclasses of `StoredObject`. Add a unique index on each
    group of keys provided.

    :param *groups: List of lists of keys to be indexed
    """
    def wrapper(cls):
        cls.__indices__ = getattr(cls, '__indices__', [])
        cls.__indices__.extend([
            {
                'key_or_list': [
                    (key, pymongo.ASCENDING)
                    for key in group
                ],
                'unique': True,
            }
            for group in groups
        ])
        return cls
    return wrapper

def get_or_http_error(Model, pk_or_query, allow_deleted=False, display_name=None):
    """Load an instance of Model by primary key or modularodm.Q query. Raise an appropriate
    HTTPError if no record is found or if the query fails to find a unique record
    :param type Model: StoredObject subclass to query
    :param pk_or_query:
    :type pk_or_query: either
      - a <basestring> representation of the record's primary key, e.g. 'abcdef'
      - a <QueryBase> subclass query to uniquely select a record, e.g.
        Q('title', 'eq', 'Entitled') & Q('version', 'eq', 1)
    :param bool allow_deleted: allow deleleted records?
    :param basestring display_name:
    :raises: HTTPError(404) if the record does not exist
    :raises: HTTPError(400) if no unique record is found
    :raises: HTTPError(410) if the resource is deleted and allow_deleted = False
    :return: Model instance
    """

    display_name = display_name or ''
    # FIXME: Not everything that uses this decorator needs to be markupsafe, but OsfWebRenderer error.mako does...
    safe_name = markupsafe.escape(display_name)

    if isinstance(pk_or_query, QueryBase):
        try:
            instance = Model.find_one(pk_or_query)
        except NoResultsFound:
            raise HTTPError(http.NOT_FOUND, data=dict(
                message_long="No {name} record matching that query could be found".format(name=safe_name)
            ))
        except MultipleResultsFound:
            raise HTTPError(http.BAD_REQUEST, data=dict(
                message_long="The query must match exactly one {name} record".format(name=safe_name)
            ))
    else:
        instance = Model.load(pk_or_query)
        if not instance:
            raise HTTPError(http.NOT_FOUND, data=dict(
                message_long="No {name} record with that primary key could be found".format(name=safe_name)
            ))
    if getattr(instance, 'is_deleted', False) and getattr(instance, 'suspended', False):
        raise HTTPError(451, data=dict(  # 451 - Unavailable For Legal Reasons
            message_short='Content removed',
            message_long='This content has been removed'
        ))
    if not allow_deleted and getattr(instance, 'is_deleted', False):
        raise HTTPError(http.GONE, data=dict(
            message_long="This {name} record has been deleted".format(name=safe_name)
        ))
    return instance


def autoload(Model, extract_key, inject_key, func):
    """Decorator to autoload a StoredObject instance by primary key and inject into kwargs. Raises
    an appropriate HTTPError (see #get_or_http_error)

    :param type Model: database collection model to query (should be a subclass of StoredObject)
    :param basestring extract_key: named URL field containing the desired primary key to be fetched
        from the database
    :param basestring inject_key: name the instance will be accessible as when it's injected as an
        argument to the function

    Example usage: ::
      def get_node(node_id):
          node = Node.load(node_id)
          ...

      becomes

      import functools
      autoload_node = functools.partial(autoload, Node, 'node_id', 'node')

      @autoload_node
      def get_node(node):
          ...
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        primary_key = kwargs.get(extract_key)
        instance = get_or_http_error(Model, primary_key)

        kwargs[inject_key] = instance
        return func(*args, **kwargs)
    return wrapper

def paginated(model, query=None, increment=200):
    last_id = ''
    pages = (model.find(query).count() / increment) + 1
    for i in xrange(pages):
        q = Q('_id', 'gt', last_id)
        if query:
            q &= query
        page = list(model.find(q).limit(increment))
        for item in page:
            yield item
        if page:
            last_id = item._id
