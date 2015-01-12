try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('FIGSHARE_PROVIDER_CONFIG', {})
