
import settings
from evernote.api.client import EvernoteClient

def get_evernote_client(token=None):
    if token:
        return EvernoteClient(token=token, sandbox=settings.EVERNOTE_SANDBOX)
    else:
        return EvernoteClient(
            consumer_key=settings.EVERNOTE_CLIENT_ID,
            consumer_secret=settings.EVERNOTE_CLIENT_SECRET,
            sandbox=settings.EVERNOTE_SANDBOX
        )
