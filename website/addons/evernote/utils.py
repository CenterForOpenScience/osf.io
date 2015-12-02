
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

def get_notebooks(client):

    noteStore = client.get_note_store()
    return [{'name': notebook.name,
             'guid': notebook.guid,
             'stack': notebook.stack,
             'defaultNotebook': notebook.defaultNotebook} for notebook in noteStore.listNotebooks()]

# https://dev.evernote.com/doc/reference/NoteStore.html#Fn_NoteStore_getNotebook

def get_notebook(client, nb_guid):
    noteStore = client.get_note_store()
    notebook = noteStore.getNotebook(nb_guid)
    return {'name': notebook.name,
             'guid': notebook.guid,
             'stack': notebook.stack,
             'defaultNotebook': notebook.defaultNotebook}
