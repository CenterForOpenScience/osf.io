import unittest

from website import settings


requires_search = unittest.skipIf(
    not settings.SEARCH_ENGINE,
    'search disabled'
)
