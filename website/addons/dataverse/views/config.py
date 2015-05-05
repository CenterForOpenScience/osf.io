# -*- coding: utf-8 -*-

import httplib as http
from flask import request
from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.project import decorators
from website.util.sanitize import assert_clean
from website.util import api_url_for, web_url_for

from website.addons.dataverse import client
from website.addons.dataverse.model import DataverseProvider
from website.addons.dataverse.settings import HOST
from website.addons.dataverse.serializer import DataverseSerializer
from website.oauth.models import ExternalAccount


@must_be_logged_in
def dataverse_get_user_accounts(auth):
    """ Returns the list of all of the current user's authorized Dataverse accounts """

    return DataverseSerializer(
        user_settings=auth.user.get_addon('dataverse')
    ).serialized_user_settings


@must_be_logged_in
def dataverse_add_external_account(auth, **kwargs):
    user = auth.user
    provider = DataverseProvider()

    host = request.json.get('host')
    api_token = request.json.get('api_token')

    # TODO: Verify/format host
    # TODO: Authenticate against server

    # Note: `DataverseSerializer` expects display_name to be a URL
    try:
        provider.account = ExternalAccount(
            provider=provider.short_name,
            provider_name=provider.name,
            display_name=host,       # no username; show host
            oauth_key=host,          # hijacked; now host
            oauth_secret=api_token,  # hijacked; now api_token
            provider_id=api_token,   # THIS IS BAD
        )
        provider.account.save()
    except KeyExistsException:
        # ... or get the old one
        provider.account = ExternalAccount.find_one(
            Q('provider', 'eq', provider.short_name) &
            Q('provider_id', 'eq', api_token)
        )
        assert provider.account is not None

    if provider.account not in user.external_accounts:
        user.external_accounts.append(provider.account)
        user.save()

    return {}


@must_be_logged_in
@decorators.must_be_valid_project
@decorators.must_have_addon('dataverse', 'node')
def dataverse_config_get(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    return {
        'result': serialize_settings(node_addon, auth.user),
    }, http.OK


@decorators.must_have_permission('write')
@decorators.must_have_addon('dataverse', 'user')
@decorators.must_have_addon('dataverse', 'node')
def dataverse_import_user_auth(auth, node_addon, user_addon, **kwargs):
    """Import dataverse credentials from the currently logged-in user to a node.
    """
    user = auth.user
    node_addon.set_user_auth(user_addon)
    node_addon.save()
    return {
        'result': serialize_settings(node_addon, user),
        'message': 'Successfully imported access token from profile.',
    }, http.OK


def serialize_settings(node_settings, current_user):
    """View helper that returns a dictionary representation of a
    DataverseNodeSettings record. Provides the return value for the
    dataverse config endpoints.
    """
    user_settings = node_settings.user_settings
    user_is_owner = user_settings is not None and (
        user_settings.owner._primary_key == current_user._primary_key
    )
    current_user_settings = current_user.get_addon('dataverse')
    result = {
        'nodeHasAuth': node_settings.has_auth,
        'userIsOwner': user_is_owner,
        'userHasAuth': current_user_settings is not None and current_user_settings.has_auth,
        'urls': serialize_urls(node_settings),
    }

    if node_settings.has_auth:
        # Add owner's profile info
        result['urls']['owner'] = web_url_for('profile_view_id',
            uid=user_settings.owner._primary_key)
        result.update({
            'ownerName': user_settings.owner.fullname,
            'apiToken': user_settings.api_token,
        })
        # Add owner's dataverse settings
        connection = client.connect_from_settings(user_settings)
        dataverses = client.get_dataverses(connection)
        result.update({
            'connected': connection is not None,
            'dataverses': [
                {'title': dataverse.title, 'alias': dataverse.alias}
                for dataverse in dataverses
            ],
            'savedDataverse': {
                'title': node_settings.dataverse,
                'alias': node_settings.dataverse_alias
            },
            'savedDataset': {
                'title': node_settings.dataset,
                'doi': node_settings.dataset_doi
            }
        })
    return result


def serialize_urls(node_settings):
    node = node_settings.owner
    urls = {
        'create': api_url_for('dataverse_set_user_config'),
        'set': node.api_url_for('set_dataverse_and_dataset'),
        'importAuth': node.api_url_for('dataverse_import_user_auth'),
        'deauthorize': node.api_url_for('deauthorize_dataverse'),
        'getDatasets': node.api_url_for('dataverse_get_datasets'),
        'datasetPrefix': 'http://dx.doi.org/',
        'dataversePrefix': 'http://{0}/dataverse/'.format(HOST),
        'apiToken': 'https://{0}/account/apitoken'.format(HOST),
        'settings': web_url_for('user_addons'),
    }
    return urls


@decorators.must_have_permission('write')
@decorators.must_have_addon('dataverse', 'user')
@decorators.must_have_addon('dataverse', 'node')
def dataverse_get_datasets(node_addon, **kwargs):
    alias = request.json.get('alias')
    user_settings = node_addon.user_settings

    connection = client.connect_from_settings(user_settings)
    dataverse = client.get_dataverse(connection, alias)
    datasets = client.get_datasets(dataverse)
    ret = {
        'datasets': [{'title': dataset.title, 'doi': dataset.doi} for dataset in datasets],
    }
    return ret, http.OK


@must_be_logged_in
def dataverse_set_user_config(auth, **kwargs):

    user = auth.user

    try:
        assert_clean(request.json)
    except AssertionError:
        # TODO: Test me!
        raise HTTPError(http.NOT_ACCEPTABLE)

    # Log in with Dataverse
    token = request.json.get('api_token')
    client.connect_or_401(token)

    user_addon = user.get_addon('dataverse')
    if user_addon is None:
        user.add_addon('dataverse')
        user_addon = user.get_addon('dataverse')

    user_addon.api_token = token
    user_addon.save()

    return {'token': token}, http.OK


@decorators.must_have_permission('write')
@decorators.must_have_addon('dataverse', 'user')
@decorators.must_have_addon('dataverse', 'node')
def set_dataverse_and_dataset(node_addon, auth, **kwargs):

    user_settings = node_addon.user_settings
    user = auth.user

    if user_settings and user_settings.owner != user:
        raise HTTPError(http.FORBIDDEN)

    try:
        assert_clean(request.json)
    except AssertionError:
        # TODO: Test me!
        raise HTTPError(http.NOT_ACCEPTABLE)

    alias = request.json.get('dataverse').get('alias')
    doi = request.json.get('dataset').get('doi')

    if doi is None:
        return HTTPError(http.BAD_REQUEST)

    connection = client.connect_from_settings(user_settings)
    dataverse = client.get_dataverse(connection, alias)
    dataset = client.get_dataset(dataverse, doi)

    node_addon.dataverse_alias = dataverse.alias
    node_addon.dataverse = dataverse.title

    node_addon.dataset_doi = dataset.doi
    node_addon.dataset_id = dataset.id
    node_addon.dataset = dataset.title

    node = node_addon.owner
    node.add_log(
        action='dataverse_dataset_linked',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'dataset': dataset.title,
        },
        auth=auth,
    )

    node_addon.save()

    return {'dataverse': dataverse.title, 'dataset': dataset.title}, http.OK
