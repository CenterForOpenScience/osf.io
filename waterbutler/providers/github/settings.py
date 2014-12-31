try:
    from waterbutler.settings import GITHUB_PROVIDER_CONFIG
except ImportError:
    GITHUB_PROVIDER_CONFIG = None

config = GITHUB_PROVIDER_CONFIG or {}


BASE_URL = config.get('BASE_URL', 'https://api.github.com/')
