# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)

from website.project.views.email import _parse_email_name


def test_parse_email_name():
    assert_equal(_parse_email_name(' Fred'), 'Fred')
    assert_equal(_parse_email_name(u'Me‰¨ü'), u'Me‰¨ü')
    assert_equal(_parse_email_name(u'Fred <fred@queen.com>'), u'Fred')
    assert_equal(_parse_email_name(u'"Fred" <fred@queen.com>'), u'Fred')
