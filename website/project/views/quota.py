from django.core.exceptions import ObjectDoesNotExist

from api.base import settings as api_settings
from website.project.decorators import must_be_contributor_or_public
from website.util import quota


@must_be_contributor_or_public
def creator_quota(auth, node, **kwargs):
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
