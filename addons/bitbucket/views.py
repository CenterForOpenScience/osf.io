"""Views for the node settings page."""
# -*- coding: utf-8 -*-
from rest_framework import status as http_status
import logging

from flask import request, make_response

from framework.exceptions import HTTPError

from addons.base import generic_views
from addons.bitbucket.api import BitbucketClient
from addons.bitbucket.apps import bitbucket_hgrid_data
from addons.bitbucket.serializer import BitbucketSerializer

from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_contributor_or_public
)
from osf.utils.permissions import WRITE

logger = logging.getLogger(__name__)


SHORT_NAME = 'bitbucket'
FULL_NAME = 'Bitbucket'

############
# Generics #
############

bitbucket_account_list = generic_views.account_list(
    SHORT_NAME,
    BitbucketSerializer
)

bitbucket_import_auth = generic_views.import_auth(
    SHORT_NAME,
    BitbucketSerializer
)

def _get_folders(node_addon, folder_id):
    pass

bitbucket_folder_list = generic_views.folder_list(
    SHORT_NAME,
    FULL_NAME,
    _get_folders
)

bitbucket_get_config = generic_views.get_config(
    SHORT_NAME,
    BitbucketSerializer
)

bitbucket_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)


#################
# Special Cased #
#################

@must_not_be_registration
@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
@must_have_permission(WRITE)
def bitbucket_set_config(auth, **kwargs):
    node_settings = kwargs.get('node_addon', None)
    node = kwargs.get('node', None)
    user_settings = kwargs.get('user_addon', None)

    try:
        if not node:
            node = node_settings.owner
        if not user_settings:
            user_settings = node_settings.user_settings
    except AttributeError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Parse request
    bitbucket_user_name = request.json.get('bitbucket_user', '')
    bitbucket_repo_name = request.json.get('bitbucket_repo', '')

    if not bitbucket_user_name or not bitbucket_repo_name:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Verify that repo exists and that user can access
    connection = BitbucketClient(access_token=node_settings.external_account.oauth_key)
    repo = connection.repo(bitbucket_user_name, bitbucket_repo_name)
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
        return {'message': message}, http_status.HTTP_400_BAD_REQUEST

    changed = (
        bitbucket_user_name != node_settings.user or
        bitbucket_repo_name != node_settings.repo
    )

    # Update hooks
    if changed:

        # # Delete existing hook, if any
        # node_settings.delete_hook()

        # Update node settings
        node_settings.user = bitbucket_user_name
        node_settings.repo = bitbucket_repo_name

        # Log repo select
        node.add_log(
            action='bitbucket_repo_linked',
            params={
                'project': node.parent_id,
                'node': node._id,
                'bitbucket': {
                    'user': bitbucket_user_name,
                    'repo': bitbucket_repo_name,
                }
            },
            auth=auth,
        )

        # # Add new hook
        # if node_settings.user and node_settings.repo:
        #     node_settings.add_hook(save=False)

        node_settings.save()

    return {}

@must_be_contributor_or_public
@must_have_addon('bitbucket', 'node')
def bitbucket_download_starball(node_addon, **kwargs):

    archive = kwargs.get('archive', 'tar')
    ref = request.args.get('sha', 'master')

    connection = BitbucketClient(access_token=node_addon.external_account.oauth_key)
    headers, data = connection.starball(
        node_addon.user, node_addon.repo, archive, ref
    )

    resp = make_response(data)
    for key, value in headers.items():
        resp.headers[key] = value

    return resp

#########
# HGrid #
#########

@must_be_contributor_or_public
@must_have_addon('bitbucket', 'node')
def bitbucket_root_folder(*args, **kwargs):
    """View function returning the root container for a Bitbucket repo. In
    contrast to other add-ons, this is exposed via the API for Bitbucket to
    accommodate switching between branches and commits.

    """
    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    data = request.args.to_dict()

    return bitbucket_hgrid_data(node_settings, auth=auth, **data)
