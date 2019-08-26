from framework.auth.decorators import must_be_signed
from osf.models import AbstractNode
from website.project.decorators import must_be_contributor_or_public
from website.util import quota
from api.base import settings as api_settings


@must_be_signed
def waterbutler_creator_quota(pid, **kwargs):
    return get_quota_from_pid(pid)

@must_be_contributor_or_public
def get_creator_quota(pid, **kwargs):
    return get_quota_from_pid(pid)

def get_quota_from_pid(pid):
    """Auxiliary function for getting the quota from a project ID.
    Used on requests by waterbutler and the user (from browser)."""
    node = AbstractNode.load(pid)
    max_quota, used_quota = quota.get_quota_info(
        node.creator, quota.get_project_storage_type(node)
    )
    return {
        'max': max_quota * api_settings.SIZE_UNIT_GB,
        'used': used_quota
    }
