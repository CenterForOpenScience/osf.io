from api.caching.tasks import ban_url
from framework.tasks.handlers import enqueue_task
from modularodm import signals

@signals.save.connect
def log_object_saved(sender, instance, fields_changed, cached_data):
    abs_url = None
    if hasattr(instance, 'absolute_api_v2_url'):
        abs_url = instance.absolute_api_v2_url

    if abs_url is not None:
        enqueue_task(ban_url.s(abs_url))
