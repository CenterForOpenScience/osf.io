try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('GITHUB_PROVIDER_CONFIG', {})


BASE_URL = config.get('BASE_URL', 'https://api.github.com/')
