# -*- coding: utf-8 -*-

import httplib as http

from flask import request

from framework.auth.decorators import must_be_logged_in
from framework.auth import get_current_user
from framework.exceptions import HTTPError

from website.project.decorators import must_have_permission, must_be_addon_authorizer, must_be_valid_project
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

from ..api import GitHub


@must_be_logged_in
def github_set_user_config(**kwargs):
    return {}


@must_have_permission('write')
@must_have_addon('github', 'node')
@must_not_be_registration
def github_set_config(**kwargs):

    auth = kwargs['auth']
    user = auth.user

    node_settings = kwargs['node_addon']
    node = node_settings.owner
    user_settings = node_settings.user_settings

    # If authorized, only owner can change settings
    if user_settings and user_settings.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    # Parse request
    github_user_name = request.json.get('github_user', '')
    github_repo_name = request.json.get('github_repo', '')

    # Verify that repo exists and that user can access
    connection = GitHub.from_settings(user_settings)
    repo = connection.repo(github_user_name, github_repo_name)
    if repo is None:
        if user_settings:
            message = (
                'Cannot access repo. Either the repo does not exist '
                'or your account does not have permission to view it.'
            )
        else:
            message = (
                'Cannot access repo.'
            )
        return {'message': message}, http.BAD_REQUEST

    if not github_user_name or not github_repo_name:
        raise HTTPError(http.BAD_REQUEST)

    changed = (
        github_user_name != node_settings.user or
        github_repo_name != node_settings.repo
    )

    # Update hooks
    if changed:

        # Delete existing hook, if any
        node_settings.delete_hook()

        # Update node settings
        node_settings.user = github_user_name
        node_settings.repo = github_repo_name

        # Log repo select
        node.add_log(
            action='github_repo_linked',
            params={
                'project': node.parent_id,
                'node': node._id,
                'github': {
                    'user': github_user_name,
                    'repo': github_repo_name,
                }
            },
            auth=auth,
        )

        # Add new hook
        if node_settings.user and node_settings.repo:
            node_settings.add_hook(save=False)

        node_settings.save()

    return {}


@must_have_permission('write')
@must_have_addon('github', 'node')
def github_set_privacy(**kwargs):

    github = kwargs['node_addon']
    private = request.form.get('private')

    if private is None:
        raise HTTPError(http.BAD_REQUEST)

    connection = GitHub.from_settings(github.user_settings)

    connection.set_privacy(github.user, github.repo, private)

# TODO delete not required functions above this
@must_be_valid_project
@must_have_addon('github', 'node')
def github_config_get(node_addon, **kwargs):
    """API that returns the serialized node settings."""
    user = get_current_user()
    return {
        'result': serialize_settings(node_addon, user),
    }, http.OK


def serialize_settings(node_settings, current_user, client=None):
    """View helper that returns a dictionary representation of a
    GithubNodeSettings record. Provides the return value for the
    github config endpoints.
    """
    user_settings = node_settings.user_settings
    user_is_owner = user_settings is not None and (
        user_settings.owner._primary_key == current_user._primary_key
    )
    current_user_settings = current_user.get_addon('github')
    print current_user_settings
    result = {
        'nodeHasAuth': node_settings.has_auth,
        'userIsOwner': user_is_owner,
        'userHasAuth': current_user_settings is not None and current_user_settings.has_auth,
        'urls': serialize_urls(node_settings),
    }
    if node_settings.has_auth:
        # Add owner's profile URL
        result['urls']['owner'] = web_url_for('profile_view_id',
            uid=user_settings.owner._primary_key)
        result['ownerName'] = user_settings.owner.fullname
        # Show available folders
        path = node_settings.folder
        if path is None:
            result['folder'] = {'name': None, 'path': None}
        else:
            result['folder'] = {
                'name': 'Github' + path,
                'path': path
            }
    return result

def serialize_urls(node_settings):
    node = node_settings.owner
    # if node_settings.folder and node_settings.folder != '/':
    #     # The link to share a the folder with other Github users
    #     share_url = utils.get_share_folder_uri(node_settings.folder)
    # else:
    #     share_url = None
    urls = {
        'config': node.api_url_for('github_config_put'),
        'deauthorize': node.api_url_for('github_deauthorize'),
        'auth': node.api_url_for('github_oauth_start'),
        'importAuth': node.api_url_for('github_import_user_auth'),
        'files': node.web_url_for('collect_file_trees'),
        # Endpoint for fetching only folders (including root)
        'folders': node.api_url_for('github_hgrid_data_contents',
            foldersOnly=1, includeRoot=1),
        # 'share': share_url,
        # 'emails': node.api_url_for('dropbox_get_share_emails')
    }
    return urls

@must_have_permission('write')
@must_not_be_registration
@must_have_addon('github', 'user')
@must_have_addon('github', 'node')
@must_be_addon_authorizer('github')
def github_config_put(node_addon, user_addon, auth, **kwargs):
    """View for changing a node's linked github folder."""
    folder = request.json.get('selected')
    path = folder['path']
    node_addon.set_folder(path, auth=auth)
    node_addon.save()
    return {
        'result': {
            'folder': {
                'name': 'Github' + path,
                'path': path
            },
            'urls': serialize_urls(node_addon)
        },
        'message': 'Successfully updated settings.',
    }, http.OK

@must_have_permission('write')
@must_have_addon('dropbox', 'user')
@must_have_addon('dropbox', 'node')
def github_import_user_auth(auth, node_addon, user_addon, **kwargs):
    """Import github credentials from the currently logged-in user to a node.
    """
    user = auth.user
    node_addon.set_user_auth(user_addon)
    node_addon.save()
    return {
        'result': serialize_settings(node_addon, user),
        'message': 'Successfully imported access token from profile.',
    }, http.OK

@must_have_permission('write')
@must_have_addon('github', 'node')
@must_not_be_registration
def github_deauthorize(auth, node_addon, **kwargs):
   node_addon.deauthorize(auth=auth)
   node_addon.save()
   return None
