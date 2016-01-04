from api.caching.tasks import ban_url, logger
from framework.guid.model import Guid
from framework.tasks.handlers import enqueue_task
from modularodm import signals

@signals.save.connect
def log_object_saved(sender, instance, fields_changed, cached_data):
    abs_url = None
    if hasattr(instance, 'absolute_api_v2_url'):
        abs_url = instance.absolute_api_v2_url
    else:
        #  I don't think this should ever happen, but ... just in case.
        guid_obj = Guid.load(instance._id)
        if guid_obj is not None:
            typedModel = guid_obj.referent
            if hasattr(typedModel, 'absolute_api_v2_url'):
                abs_url = typedModel.absolute_api_v2_url

    if abs_url is not None:
        enqueue_task(ban_url.s(abs_url))
    else:
        logger.error('Cannot ban None url for {} with id {}'.format(instance._name, instance._id))
