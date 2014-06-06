import unittest
from website import settings

requires_search = unittest.skipIf( 
    settings.SEARCH_ENGINE == 'none',
    'search disabled'
)
requires_piwik = unittest.skipIf(
    settings.PIWIK_HOST is None,
    'no PIWIK_HOST specified in settings'
)
