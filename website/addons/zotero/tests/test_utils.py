import unittest

from nose.tools import *

from website.addons.citations.utils import serialize_account


class TestSerializeAccount(unittest.TestCase):
    # TODO: Move to website/addons/citations/tests
    def test_serialize_account_none(self):
        assert_is_none(serialize_account(None))