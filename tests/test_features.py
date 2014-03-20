import unittest
from website import settings

requires_solr = unittest.skipIf(
    not settings.USE_SOLR,
    'Solr disabled'
)
requires_piwik = unittest.skipIf(
    settings.PIWIK_HOST is None,
    'no PIWIK_HOST specified in settings'
)
