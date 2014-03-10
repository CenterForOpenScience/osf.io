from website.profile.utils import reduce_permissions
import settings as gitlab_settings

def translate_permissions(permissions):
    osf_permissions = reduce_permissions(permissions)
    return gitlab_settings.ACCESS_LEVELS[osf_permissions]
