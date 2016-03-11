from functools import partial

from api.caching.tasks import ban_url
from framework.tasks.postcommit_handlers import enqueue_postcommit_task
from modularodm import signals

@signals.save.connect
def log_object_saved(sender, instance, fields_changed, cached_data):
    abs_url = None
    if hasattr(instance, 'absolute_api_v2_url'):
        abs_url = instance.absolute_api_v2_url

    if abs_url is not None:
        enqueue_postcommit_task(partial(ban_url, instance, fields_changed))
