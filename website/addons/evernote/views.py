from framework.auth.decorators import must_be_logged_in
from website.addons.evernote.serializer import EvernoteSerializer

@must_be_logged_in
def evernote_get_user_accounts(auth):
    """ Returns the list of all of the current user's authorized Evernote accounts """
    serializer = EvernoteSerializer(user_settings=auth.user.get_addon('evernote'))
    return serializer.serialized_user_settings
