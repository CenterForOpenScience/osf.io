from functools import partial

from api.caching.tasks import ban_url
from framework.postcommit_tasks.handlers import enqueue_postcommit_task
from modularodm import signals

@signals.save.connect
def ban_object_from_cache(sender, instance, fields_changed, cached_data):
    abs_url = None
    if hasattr(instance, 'absolute_api_v2_url'):
        abs_url = instance.absolute_api_v2_url

    if abs_url is not None:
        enqueue_postcommit_task(partial(ban_url, instance, fields_changed))
