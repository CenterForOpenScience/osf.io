import datetime
import unittest

from django.utils import timezone
from osf.utils import sanitize


class TestSanitize(unittest.TestCase):

    def test_strip_html(self):
        assert sanitize.strip_html('<foo>bar</foo>') == 'bar'
        assert sanitize.strip_html(b'<foo>bar</foo>') == 'bar'

    def test_strip_html_on_non_strings_returns_original_value(self):
        assert sanitize.strip_html(True)
        assert not sanitize.strip_html(False)

        assert sanitize.strip_html(12) == 12
        assert sanitize.strip_html(12.3) == 12.3

        dtime = timezone.now()
        assert sanitize.strip_html(dtime) == dtime

    def test_strip_html_sanitizes_collection_types_as_strings(self):
        assert sanitize.strip_html({'foo': '<b>bar</b>'}) == "{'foo': 'bar'}"
        assert sanitize.strip_html(['<em>baz</em>']) == "['baz']"

    def test_unescape_html(self):
        assert sanitize.unescape_entities('&lt;&gt; diamonds &amp; diamonds &lt;&gt;') == '&lt;&gt; diamonds & diamonds &lt;&gt;'
        assert sanitize.unescape_entities(['&lt;&gt;&amp;'])[0] == '&lt;&gt;&'
        assert sanitize.unescape_entities(('&lt;&gt;&amp;', ))[0] =='&lt;&gt;&'
        assert sanitize.unescape_entities({'key': '&lt;&gt;&amp;'})['key'] =='&lt;&gt;&'

    def test_unescape_html_additional_safe_characters(self):
        assert sanitize.unescape_entities(
                '&lt;&gt; diamonds &amp; diamonds &lt;&gt;',
                safe={
                    '&lt;': '<',
                    '&gt;': '>'
                }
            ) == '<> diamonds & diamonds <>'
        assert sanitize.unescape_entities(
                ['&lt;&gt;&amp;'],
                safe={
                    '&lt;': '<',
                    '&gt;': '>'
                }
            )[0] == '<>&'
        assert sanitize.unescape_entities(
                ('&lt;&gt;&amp;', ),
                safe={
                    '&lt;': '<',
                    '&gt;': '>'
                }
            )[0] == '<>&'
        assert sanitize.unescape_entities(
                {'key': '&lt;&gt;&amp;'},
                safe={
                    '&lt;': '<',
                    '&gt;': '>'
                }
            )['key'] == '<>&'

    def test_safe_json(self):
        """Add escaping of forward slashes, but only where string literal contains closing markup"""
        assert sanitize.safe_json("I'm a string with / containing </closingtags>") == '"I\'m a string with / containing <\\/closingtags>"'
