from stevedore import extension

try:
    from waterbutler.settings import TASKS_CONFIG
except ImportError:
    TASKS_CONFIG = None

config = TASKS_CONFIG or {}


BROKER_URL = config.get('BROKER_URL', 'amqp://')
CELERY_RESULT_BACKEND = config.get('CELERY_RESULT_BACKEND', 'redis://')
CELERY_DISABLE_RATE_LIMITS = config.get('CELERY_DISABLE_RATE_LIMITS', True)
CELERY_TASK_RESULT_EXPIRES = config.get('CELERY_TASK_RESULT_EXPIRES', 60)
# CELERY_ALWAYS_EAGER = config.get('CELERY_ALWAYS_EAGER', True)
CELERY_IMPORTS = config.get('CELERY_IMPORTS', tuple([
    e.plugin.__name__
    for e in extension.ExtensionManager(
        namespace='waterbutler.providers.tasks',
    ).extensions
]))
