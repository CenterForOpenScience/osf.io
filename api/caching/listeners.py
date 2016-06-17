from api.caching.tasks import ban_url
from framework.postcommit_tasks.handlers import enqueue_postcommit_task
from modularodm import signals

@signals.save.connect
def ban_object_from_cache(sender, instance, fields_changed, cached_data):
    if hasattr(instance, 'absolute_api_v2_url'):
        enqueue_postcommit_task(ban_url, (instance, ), {})
