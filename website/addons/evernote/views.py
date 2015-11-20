from framework.auth.decorators import must_be_logged_in
from website.addons.evernote.serializer import EvernoteSerializer

from website.util import permissions
from website.project.decorators import (
    must_have_addon,
    must_have_permission
)

@must_be_logged_in
def evernote_get_user_accounts(auth):
    """ Returns the list of all of the current user's authorized Evernote accounts """
    serializer = EvernoteSerializer(user_settings=auth.user.get_addon('evernote'))
    return serializer.serialized_user_settings


@must_have_addon('evernote', 'node')
#@must_have_permission(permissions.WRITE)
def evernote_get_config(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    # following from box addon:
    # if node_addon.external_account:
    #     refresh_oauth_key(node_addon.external_account)

    return {
        'result': EvernoteSerializer().serialize_settings(node_addon, auth.user),
    }
