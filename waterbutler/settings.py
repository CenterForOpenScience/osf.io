import os
import json
import logging
import logging.config


PROJECT_NAME = 'waterbutler'
PROJECT_CONFIG_PATH = '~/.cos'

DEFAULT_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(cyan)s[%(asctime)s]%(log_color)s[%(levelname)s][%(name)s]: %(reset)s%(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'console'
        },
        'syslog': {
            'class': 'logging.handlers.SysLogHandler',
            'level': 'INFO'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
}


try:
    config_path = os.environ['{}_CONFIG'.format(PROJECT_NAME.upper())]
except KeyError:
    env = os.environ.get('ENV', 'test')
    config_path = '{}/{}-{}.json'.format(PROJECT_CONFIG_PATH, PROJECT_NAME, env)


config = {}
config_path = os.path.expanduser(config_path)
if not os.path.exists(config_path):
    logging.warning('No \'{}\' configuration file found'.format(config_path))
else:
    with open(os.path.expanduser(config_path)) as fp:
        config = json.load(fp)


def get(key, default):
    return config.get(key, default)


logging_config = get('LOGGING', DEFAULT_LOGGING_CONFIG)
logging.config.dictConfig(logging_config)
