try:
    from waterbutler.settings import S3_PROVIDER_CONFIG
except ImportError:
    S3_PROVIDER_CONFIG = None

config = S3_PROVIDER_CONFIG or {}


TEMP_URL_SECS = config.get('TEMP_URL_SECS', 100)
