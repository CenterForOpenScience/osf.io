# -*- coding: utf-8 -*-
import functools
from rest_framework import status as http_status

import markupsafe
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from flask import request

from framework.exceptions import HTTPError
from osf.utils.requests import check_select_for_update


def get_or_http_error(Model, pk_or_query, allow_deleted=False, display_name=None):
    """Load an instance of Model by primary key or query. Raise an appropriate
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
    select_for_update = check_select_for_update(request)

    if isinstance(pk_or_query, Q):
        try:
            instance = Model.objects.filter(pk_or_query).select_for_update().get() if select_for_update else Model.objects.get(pk_or_query)
        except Model.DoesNotExist:
            raise HTTPError(http_status.HTTP_404_NOT_FOUND, data=dict(
                message_long='No {name} record matching that query could be found'.format(name=safe_name)
            ))
        except Model.MultipleObjectsReturned:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
                message_long='The query must match exactly one {name} record'.format(name=safe_name)
            ))
    else:
        instance = Model.load(pk_or_query, select_for_update=select_for_update)
        if not instance:
            raise HTTPError(http_status.HTTP_404_NOT_FOUND, data=dict(
                message_long='No {name} record with that primary key could be found'.format(name=safe_name)
            ))
    if getattr(instance, 'is_deleted', False) and getattr(instance, 'suspended', False):
        raise HTTPError(451, data=dict(  # 451 - Unavailable For Legal Reasons
            message_short='Content removed',
            message_long='This content has been removed'
        ))
    if not allow_deleted and getattr(instance, 'is_deleted', False):
        raise HTTPError(http_status.HTTP_410_GONE)
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


def paginated(model, query=None, increment=200, each=True, include=None):
    """Paginate a MODM query.

    :param StoredObject model: Model to query.
    :param Q query: Optional query object.
    :param int increment: Page size
    :param bool each: If True, each record is yielded. If False, pages
        are yielded.
    """
    if include and query:
        queryset = model.objects.filter(query).include(*include)
    elif query:
        queryset = model.objects.filter(query)
    else:
        queryset = model.objects.all()

    # Pagination requires an order by clause, especially when using Postgres.
    # see: https://docs.djangoproject.com/en/1.10/topics/pagination/#required-arguments
    if isinstance(queryset, QuerySet) and not queryset.ordered:
        queryset = queryset.order_by(queryset.model._meta.pk.name)

    paginator = Paginator(queryset.all(), increment)
    for page_num in paginator.page_range:
        page = paginator.page(page_num)
        if each:
            for item in page.object_list:
                yield item
        else:
            yield page.object_list
