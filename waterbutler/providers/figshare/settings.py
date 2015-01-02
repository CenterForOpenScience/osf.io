try:
    from waterbutler.settings import FIGSHARE_PROVIDER_CONFIG
except ImportError:
    S3_PROVIDER_CONFIG = {}

config = FIGSHARE_PROVIDER_CONFIG or {}
