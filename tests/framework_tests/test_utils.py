import unittest  # noqa
from nose.tools import *  # noqa

from modularodm import Q

from tests.base import DbTestCase
from tests import factories

from framework.mongo.utils import get_or_http_error, autoload
from framework.exceptions import HTTPError

from website.models import Node


class MongoUtilsTestCase(DbTestCase):

    def test_get_or_http_error_by_pk_found(self):
        n = factories.NodeFactory()
        found = get_or_http_error(Node, n._id)
        assert_equal(found, n)

    def test_get_or_http_error_by_pk_not_found(self):
        with assert_raises(HTTPError):
            get_or_http_error(Node, 'blah')

    def test_get_or_http_error_by_query_found(self):
        n = factories.NodeFactory()
        found = get_or_http_error(
            Node,
            (Q('title', 'eq', n.title) & Q('_id', 'eq', n._id))
        )
        assert_equal(found, n)

    def test_get_or_http_error_by_query_not_found(self):
        with assert_raises(HTTPError):
            get_or_http_error(Node, Q('_id', 'eq', 'blah'))

    def test_get_or_http_error_by_query_not_unique(self):
        title = 'TITLE'
        factories.NodeFactory(title=title)
        factories.NodeFactory(title=title)
        with assert_raises(HTTPError):
            get_or_http_error(Node, Q('title', 'eq', title))

    def test_autoload(self):

        target = factories.NodeFactory()

        def fn(node, *args, **kwargs):
            return node

        wrapped = autoload(Node, 'node_id', 'node', fn)
        found = wrapped(node_id=target._id)
        assert_equal(found, target)
