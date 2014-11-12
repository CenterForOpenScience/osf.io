import unittest
from nose.tools import *
from website.util import sanitize


class TestSanitize(unittest.TestCase):

    def test_strip_html(self):
        assert_equal(
            sanitize.strip_html('<foo>bar</foo>'),
            'bar'
        )