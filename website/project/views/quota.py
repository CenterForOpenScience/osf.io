from framework.auth.decorators import must_be_signed
from osf.models import AbstractNode, ProjectStorageType
from website.util import quota


@must_be_signed
def creator_quota(pid, **kwargs):
    node = AbstractNode.load(pid)
    try:
        storage_type = ProjectStorageType.objects.get(node=node).storage_type
    except ProjectStorageType.DoesNotExist:
        storage_type = ProjectStorageType.NII_STORAGE
    max_quota, used_quota = quota.get_quota_info(node.creator, storage_type)
    return {
        'max': max_quota * 1024 ** 3,
        'used': used_quota
    }
