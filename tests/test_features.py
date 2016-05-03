import unittest

from website import settings


requires_search = unittest.skipIf(
    not settings.SEARCH_ENGINE,
    'search disabled'
)
requires_gnupg = unittest.skipIf(
    not settings.USE_GNUPG,
    'gnupg disabled'
)
