import unittest
from nose.tools import *
from website.util import sanitize


class TestSanitize(unittest.TestCase):
    def setUp(self):
        self.dirty_text = [
            '<script> evil code </script>',
            '<img src=javascript:moreevil><img>',
            '<iframe src=evilsite>',
            '\'\'\'\'\'"""""""',
            '");</span><script></script><span>'
        ]
        self.expected = [
            '&lt;script&gt; evil code &lt;/script&gt;',
            '&lt;img src=&quot;javascript:moreevil&quot;&gt;&lt;img&gt;',
            '&lt;iframe src=&quot;evilsite&quot;&gt;',
            '&quot;&quot;&quot;&quot;&quot;&quot;&quot;',
            '&quot;);&lt;/span&gt;&lt;script&gt;&lt;/script&gt;&lt;span&gt;'
        ]

    def test_escape_html(self):
        for dirty, clean in zip(self.dirty_text, self.expected):
            assert_equal(sanitize.clean_tag(dirty), clean)

    def test_deep_clean(self):
        assert_equal(sanitize.deep_clean(self.dirty_text, cleaner=sanitize.clean_tag), self.expected)
