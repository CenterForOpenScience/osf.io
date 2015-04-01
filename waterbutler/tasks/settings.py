import os

from pkg_resources import iter_entry_points

try:
    from waterbutler import settings
except ImportError:
    settings = {}

config = settings.get('TASKS_CONFIG', {})


BROKER_URL = config.get(
    'BROKER_URL',
    'amqp://{}:{}//'.format(
        os.environ.get('RABBITMQ_PORT_5672_TCP_ADDR', ''),
        os.environ.get('RABBITMQ_PORT_5672_TCP_PORT', ''),
    )
)
CELERY_RESULT_BACKEND = config.get('CELERY_RESULT_BACKEND', None)
CELERY_DISABLE_RATE_LIMITS = config.get('CELERY_DISABLE_RATE_LIMITS', True)
CELERY_TASK_RESULT_EXPIRES = config.get('CELERY_TASK_RESULT_EXPIRES', 60)
# CELERY_ALWAYS_EAGER = config.get('CELERY_ALWAYS_EAGER', True)
CELERY_IMPORTS = [
    entry.module_name
    for entry in iter_entry_points(group='waterbutler.providers.tasks', name=None)
]

CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
REDIS_HOST = config.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(config.get('REDIS_PORT', 6379))
