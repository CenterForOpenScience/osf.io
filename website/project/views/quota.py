from framework.auth.decorators import must_be_signed
from osf.models import AbstractNode
from website.util import quota


@must_be_signed
def creator_quota(pid, **kwargs):
    node = AbstractNode.load(pid)
    max_quota, used_quota = quota.get_quota_info(
        node.creator, quota.get_project_storage_type(node)
    )
    return {
        'max': max_quota * 1024 ** 3,
        'used': used_quota
    }
