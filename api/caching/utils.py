from django.core.cache import caches
from django.conf import settings

storage_usage_cache = caches[settings.STORAGE_USAGE_CACHE_NAME]
