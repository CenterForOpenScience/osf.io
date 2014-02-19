import unittest
from nose.tools import *
from website import settings

REQUIRED_MODULES = (
    # required for full functionality of MFR
    'IPython',
    'pandas',
    'xlrd',
    'rpy2',
)

@nottest
def make_module_test(module):

    def func():
        try:
            __import__(module)
        except ImportError:
            assert False, '%s is not importable' % module
    func_name = 'test_%s_importable' % module
    func.__name__ = func_name
    globals()[func_name] = func

for m in REQUIRED_MODULES:
    make_module_test(m)

def test_piwik_enabled():
    assert_true(settings.PIWIK_HOST is not None)

requires_piwik = unittest.skipIf(
    settings.PIWIK_HOST is None,
    'no PIWIK_HOST specified in settings'
)
