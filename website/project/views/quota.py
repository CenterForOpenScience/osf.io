from django.core.exceptions import ObjectDoesNotExist

from api.base import settings as api_settings
from framework.auth.decorators import must_be_signed
from osf.models import AbstractNode
from website.util import quota


@must_be_signed
def creator_quota(pid, **kwargs):
    node = AbstractNode.load(pid)
    try:
        max_quota = node.creator.userquota.max_quota
        used_quota = node.creator.userquota.used
    except ObjectDoesNotExist:
        max_quota = api_settings.DEFAULT_MAX_QUOTA
        used_quota = quota.used_quota(node.creator._id)
    return {
        'max': max_quota * 1024 ** 3,
        'used': used_quota
    }
