from api.caching.tasks import ban_url
from framework.guid.model import signals as guid_signals, Guid


@guid_signals.guid_stored_object_saved.connect
def log_object_saved(sender, guid_stored_object):
    if hasattr(guid_stored_object, 'absolute_api_v2_url'):
        ban_url.delay(guid_stored_object.absolute_url)
    else:
        #  I don't think this should ever happen, but ... just in case.
        typedModel = Guid.load(guid_stored_object._id).referent
        if hasattr(typedModel, 'absolute_api_v2_url'):
            ban_url.delay(typedModel.absolute_url)
