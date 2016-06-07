import uuid

import psycopg2
from django.conf import settings
from django.db.backends import utils
from django.db.backends.postgresql.base import \
    DatabaseWrapper as PostgresqlDatabaseWrapper
from django.db.backends.postgresql.base import *


class server_side_cursors(object):
    """
    With block helper that enables and disables server side cursors.
    """

    def __init__(self, qs_or_using_or_connection, itersize=2000):
        from django.db import connections
        from django.db.models.query import QuerySet

        self.itersize = itersize
        if isinstance(qs_or_using_or_connection, QuerySet):
            self.connection = connections[qs_or_using_or_connection.db]
        elif isinstance(qs_or_using_or_connection, basestring):
            self.connection = connections[qs_or_using_or_connection]
        else:
            self.connection = qs_or_using_or_connection

    def __enter__(self):
        self.connection.server_side_cursors = True
        self.connection.server_side_cursor_itersize = self.itersize

    def __exit__(self, type, value, traceback):
        self.connection.server_side_cursors = False
        self.connection.server_side_cursor_itersize = None


class DatabaseWrapper(PostgresqlDatabaseWrapper):
    """
    Psycopg2 database backend that allows the use of server side cursors.

    Usage:

    qs = Model.objects.all()
    with server_side_cursors(qs, itersize=x):
        for item in qs.iterator():
            item.value
    """

    def __init__(self, *args, **kwargs):
        self.server_side_cursors = False
        self.server_side_cursor_itersize = None

        super(DatabaseWrapper, self).__init__(*args, **kwargs)

    def create_cursor(self):
        if not self.server_side_cursors:
            return super(DatabaseWrapper, self).create_cursor()

        cursor = self.connection.cursor(
            name='osf_models.db.backends.postgresql_cursors:{}'.format(
                uuid.uuid4().hex),
            cursor_factory=psycopg2.extras.DictCursor, )
        cursor.tzinfo_factory = utc_tzinfo_factory if settings.USE_TZ else None
        cursor.itersize = self.server_side_cursor_itersize

        return cursor
