import datetime
import unittest

from django.utils import timezone
from nose.tools import *  # noqa: F403
from osf.utils import sanitize
from tests.base import OsfTestCase


class TestSanitize(OsfTestCase):

    def test_strip_html(self):
        assert_equal(
            sanitize.strip_html('<foo>bar</foo>'),
            'bar'
        )
        assert_equal(
            sanitize.strip_html(b'<foo>bar</foo>'),
            'bar'
        )

    def test_strip_html_on_non_strings_returns_original_value(self):
        assert_true(sanitize.strip_html(True))
        assert_false(sanitize.strip_html(False))

        assert_equal(sanitize.strip_html(12), 12)
        assert_equal(sanitize.strip_html(12.3), 12.3)

        dtime = timezone.now()
        assert_equal(sanitize.strip_html(dtime), dtime)

    def test_strip_html_sanitizes_collection_types_as_strings(self):
        assert_equal(sanitize.strip_html({'foo': '<b>bar</b>'}), "{'foo': 'bar'}")
        assert_equal(sanitize.strip_html(['<em>baz</em>']), "['baz']")

    def test_unescape_html(self):
        assert_equal(
            sanitize.unescape_entities('&lt;&gt; diamonds &amp; diamonds &lt;&gt;'),
            '&lt;&gt; diamonds & diamonds &lt;&gt;'
        )
        assert_equal(
            sanitize.unescape_entities(['&lt;&gt;&amp;'])[0],
            '&lt;&gt;&'
        )
        assert_equal(
            sanitize.unescape_entities(('&lt;&gt;&amp;', ))[0],
            '&lt;&gt;&'
        )
        assert_equal(
            sanitize.unescape_entities({'key': '&lt;&gt;&amp;'})['key'],
            '&lt;&gt;&'
        )

    def test_unescape_html_additional_safe_characters(self):
        assert_equal(
            sanitize.unescape_entities(
                '&lt;&gt; diamonds &amp; diamonds &lt;&gt;',
                safe={
                    '&lt;': '<',
                    '&gt;': '>'
                }
            ),
            '<> diamonds & diamonds <>'
        )
        assert_equal(
            sanitize.unescape_entities(
                ['&lt;&gt;&amp;'],
                safe={
                    '&lt;': '<',
                    '&gt;': '>'
                }
            )[0],
            '<>&'
        )
        assert_equal(
            sanitize.unescape_entities(
                ('&lt;&gt;&amp;', ),
                safe={
                    '&lt;': '<',
                    '&gt;': '>'
                }
            )[0],
            '<>&'
        )
        assert_equal(
            sanitize.unescape_entities(
                {'key': '&lt;&gt;&amp;'},
                safe={
                    '&lt;': '<',
                    '&gt;': '>'
                }
            )['key'],
            '<>&'
        )

    def test_safe_json(self):
        """Add escaping of forward slashes, but only where string literal contains closing markup"""
        assert_equal(
            sanitize.safe_json("I'm a string with / containing </closingtags>"),
                               '"I\'m a string with / containing <\\/closingtags>"'
        )
