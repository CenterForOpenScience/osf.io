import os
import unittest

from website import settings


requires_search = unittest.skipIf(
    not settings.SEARCH_ENGINE,
    'search disabled'
)
requires_piwik = unittest.skipIf(
    settings.PIWIK_HOST is None,
    'no PIWIK_HOST specified in settings'
)
requires_gnupg = unittest.skipIf(
    not settings.USE_GNUPG,
    'gnupg disabled'
)
requires_csl_styles = unittest.skipIf(
    not os.path.exists(os.path.join(settings.CITATION_STYLES_PATH, '.git')),
    'CSL styles not detected'
)