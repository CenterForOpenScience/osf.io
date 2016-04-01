from flask import request
import httplib as http

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError, PermissionsError

from website.addons.evernote import utils
from website.addons.evernote.serializer import EvernoteSerializer
from website.oauth.models import ExternalAccount
from website.util import permissions
from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon,
    must_be_addon_authorizer,
    must_not_be_registration,
    must_have_permission
)

import ENML2HTML

import logging
logger = logging.getLogger(__name__)

@must_be_logged_in
def evernote_get_user_settings(auth):
    """ Returns the list of all of the current user's authorized Evernote accounts """
    serializer = EvernoteSerializer(user_settings=auth.user.get_addon('evernote'))
    return serializer.serialized_user_settings


@must_have_addon('evernote', 'node')
@must_have_permission(permissions.WRITE)
def evernote_get_config(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    # following from box addon:
    # if node_addon.external_account:
    #     refresh_oauth_key(node_addon.external_account)

    #logger.debug(node_addon)
    return {
        'result': EvernoteSerializer().serialize_settings(node_addon, auth.user),
    }

@must_not_be_registration
@must_have_addon('evernote', 'user')
@must_have_addon('evernote', 'node')
@must_be_addon_authorizer('evernote')
@must_have_permission(permissions.WRITE)
def evernote_set_config(node_addon, user_addon, auth, **kwargs):
    """View for changing a node's linked Evernote folder."""
    folder = request.json.get('selected')
    serializer = EvernoteSerializer(node_settings=node_addon)

    uid = folder['id']
    path = folder['path']

    node_addon.set_folder(uid, auth=auth)

    return {
        'result': {
            'folder': {
                'name': path.replace('All Files', '') if path != 'All Files' else '/ (Full Evernote)',
                'path': path,
            },
            'urls': serializer.addon_serialized_urls,
        },
        'message': 'Successfully updated settings.',
    }


@must_have_addon('evernote', 'user')
@must_have_addon('evernote', 'node')
@must_have_permission(permissions.WRITE)
def evernote_add_user_auth(auth, node_addon, user_addon, **kwargs):
    """Import evernote credentials from the currently logged-in user to a node.
    """
    external_account = ExternalAccount.load(
        request.json['external_account_id']
    )

    if external_account not in user_addon.external_accounts:
        raise HTTPError(http.FORBIDDEN)

    try:
        node_addon.set_auth(external_account, user_addon.owner)
    except PermissionsError:
        raise HTTPError(http.FORBIDDEN)

    node_addon.set_user_auth(user_addon)
    node_addon.save()

    return {
        'result': EvernoteSerializer().serialize_settings(node_addon, auth.user),
        'message': 'Successfully imported access token from profile.',
    }


@must_have_addon('evernote', 'node')
@must_be_addon_authorizer('evernote')
def evernote_notes(node_addon, **kwargs):

    token = node_addon.external_account.oauth_key
    client = utils.get_evernote_client(token)

    # will want to pick up notes for the notebook
    # start with calculating the number of notes in nb

    notes = utils.notes_metadata(client,
                    notebookGuid=node_addon.folder_id,
                    includeTitle=True,
                    includeUpdated=True,
                    includeCreated=True)

    results = [{'title': note.title,
              'guid': note.guid,
              'created': note.updated,
              'updated': note.created}
              for note in notes]

    return results

@must_have_addon('evernote', 'node')
@must_be_addon_authorizer('evernote')
def evernote_note(node_addon, noteid, **kwargs):

    token = node_addon.external_account.oauth_key
    client = utils.get_evernote_client(token)
    note = utils.get_note(client, noteid,
        withContent=True,
        withResourcesData=False)

    # convert to HTML
    mediaStore = utils.MyMediaStore(client.get_note_store(), note.guid)
    html = ENML2HTML.ENMLToHTML(note.content, pretty=True, header=False,
          media_store=mediaStore)

    return {'noteid': noteid,
            'content': note.content,
            'html': html}

@must_have_addon('evernote', 'node')
@must_be_addon_authorizer('evernote')
def evernote_folder_list(node_addon, **kwargs):
    """Returns a list of notebooks in Evernote"""
    if not node_addon.has_auth:
        raise HTTPError(http.FORBIDDEN)

    node = node_addon.owner
    folder_id = request.args.get('notebookId')

    # now grab the notebook list

    # figure out how to recast into the format that the folderpicker likes

    if folder_id is None:
        return [{
            'id': '0',
            'path': 'All Notes',
            'addon': 'evernote',
            'kind': 'folder',
            'name': '/ (Full Evernote)',
            'urls': {
                'folders': node.api_url_for('evernote_folder_list', notebookId='0'),
            }
        }]
    elif folder_id == '0':

        # return all the notebooks
        # stacks can contain noteboooks but not other stacks
        # first pass: ignore stacks

        # if I incorporate stacks, any setting to not allow it to be selected.

        token = node_addon.external_account.oauth_key
        client = utils.get_evernote_client(token)
        notebooks = utils.get_notebooks(client)

        return [{
            'id': notebook['guid'],
            'path': notebook['name'],
            'addon': 'evernote',
            'kind': 'folder',
            'name': notebook['name'],
            'urls': {
                'folders': node.api_url_for('evernote_folder_list', notebookId=notebook['guid']),
            }

        } for notebook in notebooks]
    else:
        return []

@must_be_contributor_or_public
@must_have_addon('evernote', 'node')
def evernote_widget(node_addon, **kwargs):
    """Collects and serializes settting needed to build the widget."""

    #provider = ZoteroCitationsProvider()
    #return provider.widget(node_addon)

    ret = node_addon.config.to_json()
    ret.update({
        'complete': node_addon.complete,
        'folder_id': node_addon.folder_id,
        'folder_name': node_addon.folder_name
    })

    return ret
