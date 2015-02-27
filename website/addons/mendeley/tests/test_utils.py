import unittest

from nose.tools import *

from website.addons.mendeley.utils import serialize_account


class TestSerializeAccount(unittest.TestCase):
    def test_serialize_account_none(self):
        assert_is_none(serialize_account(None))