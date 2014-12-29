import os
import sys

PROJECT_NAME = 'waterbutler'
PROJECT_CONFIG_PATH = '~/.cos'

try:
    config_path = os.environ['{}_CONFIG'.format(PROJECT_NAME.upper())]
except KeyError:
    env = os.environ.get('ENV', 'test')
    config_path = '{}/{}-{}.json'.format(PROJECT_CONFIG_PATH, PROJECT_NAME, env)


class _Settings:
    import hashlib
    DEFAULT = {
        'PORT': 7777,
        'ADDRESS': '127.0.0.1',
        'DEBUG': True,
        'HMAC_SECRET': 'changeme',
        'HMAC_ALGORITHM': hashlib.sha256
    }

    def __init__(self, config_path):
        import os
        import json
        import logging

        if not os.path.exists(config_path):
            self.local = {}
            logger = logging.getLogger(__name__)
            logger.warning('No local settings found, using defaults')
        else:
            self.local = json.loads(os.abspath('~/.waterbutler.json'))

    def __getattr__(self, key):
        try:
            return self.local.get(key, self.DEFAULT[key])
        except KeyError:
            raise AttributeError('Not setting for {}'.format(key))

sys.modules[__name__] = _Settings(config_path)
