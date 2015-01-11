import os

from stevedore import extension


try:
    from waterbutler.settings import TASKS_CONFIG
except ImportError:
    TASKS_CONFIG = None

config = TASKS_CONFIG or {}


BROKER_URL = config.get('BROKER_URL', 'amqp://{}:{}'.format(
    os.environ.get('RABBITMQ_PORT_5672_TCP_ADDR', ''),
    os.environ.get('RABBITMQ_PORT_5672_TCP_PORT', ''),
))
CELERY_RESULT_BACKEND = config.get('CELERY_RESULT_BACKEND', 'redis://{}:{}'.format(
    os.environ.get('REDIS_PORT_6379_TCP_ADDR', ''),
    os.environ.get('REDIS_PORT_6379_TCP_PORT', ''),
))
CELERY_DISABLE_RATE_LIMITS = config.get('CELERY_DISABLE_RATE_LIMITS', True)
CELERY_TASK_RESULT_EXPIRES = config.get('CELERY_TASK_RESULT_EXPIRES', 60)
# CELERY_ALWAYS_EAGER = config.get('CELERY_ALWAYS_EAGER', True)
CELERY_IMPORTS = config.get('CELERY_IMPORTS', tuple([
    e.plugin.__name__
    for e in extension.ExtensionManager(
        namespace='waterbutler.providers.tasks',
    ).extensions
]))
