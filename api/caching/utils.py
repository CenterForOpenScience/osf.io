from functools import partial
from django.core.cache import get_cache
from api.caching import settings

storage_usage_cache = partial(get_cache, settings.STORAGE_USAGE_CACHE_NAME)
