from nose.tools import *  # noqa

from api.base import utils as api_utils

from tests.base import ApiTestCase

class DummyAttrAttr(object):

    def __init__(self, key):
        self.key = key


class DummyAttr(object):

    def __init__(self, key):
        self.key = key
        self.attr_attr = DummyAttrAttr(key.upper())


class Dummy(object):

    def __init__(self, key):
        self.attr = DummyAttr(key)
        self.hash = {
            'bang': DummyAttr(key)
        }


class APIUtilsTestCase(ApiTestCase):

    def setUp(self):

        self.dummy = Dummy('foo')
        self.data = {
            'foo': {
                'bar': 'baz'
            }
        }

    def test_deep_get_object(self):

        attr = api_utils.deep_get(self.dummy, 'attr')
        assert_true(isinstance(attr, DummyAttr))
        assert_equal(attr.key, 'foo')

    def test_deep_get_object_multiple_depth(self):

        attr_attr = api_utils.deep_get(self.dummy, 'attr.attr_attr')
        assert_true(isinstance(attr_attr, DummyAttrAttr))
        assert_equal(attr_attr.key, 'FOO')

    def test_deep_get_dict(self):

        foo = api_utils.deep_get(self.data, 'foo')
        assert_true(isinstance(foo, dict))
        assert_equal(foo, {
            'bar': 'baz'
        })

    def test_deep_get_dict_multiple_depth(self):

        bar = api_utils.deep_get(self.data, 'foo.bar')
        assert_true(isinstance(bar, str))
        assert_equal(bar, 'baz')

    def test_deep_get_object_and_dict(self):

        hash_bang_attr = api_utils.deep_get(self.dummy, 'hash.bang.attr_attr')
        assert_true(isinstance(hash_bang_attr, DummyAttrAttr))
        assert_equal(hash_bang_attr.key, 'FOO')

    def test_deep_get_key_not_found(self):

        hash_bang_attr = api_utils.deep_get(self.dummy, 'hash.bang.baz')
        assert_equal(hash_bang_attr, None)

    def test_soft_get_object(self):

        attr = api_utils.soft_get(self.dummy, 'attr')
        assert_equal(attr.key, 'foo')

    def test_soft_get_object_not_found(self):

        bat = api_utils.soft_get(self.dummy, 'bat')
        assert_equal(bat, None)

    def test_soft_get_dict(self):

        foo = api_utils.soft_get(self.data, 'foo')
        assert_equal(foo, {
            'bar': 'baz'
        })

    def test_soft_get_dict_not_found(self):

        bat = api_utils.soft_get(self.data, 'bat')
        assert_equal(bat, None)
