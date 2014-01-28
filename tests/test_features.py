import unittest

from nose.tools import *

from website import settings

def test_piwik_enabled():
    assert_true(settings.PIWIK_HOST is not None)

requires_piwik = unittest.skipIf(
    settings.PIWIK_HOST is None,
    'no PIWIK_HOST specified in settings'
)