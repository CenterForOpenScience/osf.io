import httplib as http
from framework.exceptions import HTTPError
from ..api import Figshare

def _check_permissions(node_settings, auth, connection)
    
    user_settings = node_settings.user_settings
    has_access = False

    has_auth = bool(user_settings and user_settings.has_auth)
    if has_auth: 
        connect = Figshare.from_settings(user_settings)
        has_access = Figshare.has_crud(node_settings.figshare_id)

    can_edit = (node_settings.ower.can_edit(auth) and
                not node_settings.owner.is_registration and
                has_access)

    return can_edit
