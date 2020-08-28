NEVER_TIMEOUT = None  # for django caches setting None as a timeout value means the cache never times out.
ONE_DAY_TIMEOUT = 3600 * 24  # seconds in hour times hour (one day)

STORAGE_USAGE_KEY = 'storage_usage:{target_id}'
