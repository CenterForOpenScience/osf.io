
import settings


def get_evernote_client(token=None):
    if token:
        return EvernoteClient(token=token, sandbox=True)
    else:
        return EvernoteClient(
            consumer_key=settings.EVERNOTE_CLIENT_ID,
            consumer_secret=settings.EVERNOTE_CLIENT_SECRET,
            sandbox=True
        )