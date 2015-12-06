# -*- coding: utf-8 -*-

import httplib as http

from flask import request
from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from website.project import decorators
from website.util.sanitize import assert_clean
from website.addons.dataverse import client
from website.addons.dataverse.provider import DataverseProvider
from website.addons.dataverse.serializer import DataverseSerializer
from website.oauth.models import ExternalAccount


@must_be_logged_in
def dataverse_get_user_accounts(auth):
    """ Returns the list of all of the current user's authorized Dataverse accounts """

    return DataverseSerializer(
        user_settings=auth.user.get_addon('dataverse')
    ).serialized_user_settings


@must_be_logged_in
def dataverse_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""
    user = auth.user
    provider = DataverseProvider()

    host = request.json.get('host').rstrip('/')
    api_token = request.json.get('api_token')

    # Verify that credentials are valid
    client.connect_or_error(host, api_token)

    # Note: `DataverseSerializer` expects display_name to be a URL
    try:
        provider.account = ExternalAccount(
            provider=provider.short_name,
            provider_name=provider.name,
            display_name=host,       # no username; show host
            oauth_key=host,          # hijacked; now host
            oauth_secret=api_token,  # hijacked; now api_token
            provider_id=api_token,   # Change to username if Dataverse allows
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

    user_addon = auth.user.get_addon('dataverse')
    if not user_addon:
        user.add_addon('dataverse')
    user.save()

    # Need to ensure that the user has dataverse enabled at this point
    user.get_or_add_addon('dataverse', auth=auth)
    user.save()

    return {}


@must_be_logged_in
@decorators.must_be_valid_project
@decorators.must_have_addon('dataverse', 'node')
def dataverse_get_config(node_addon, auth, **kwargs):
    """API that returns the serialized node settings."""
    result = DataverseSerializer(
        user_settings=auth.user.get_addon('dataverse'),
        node_settings=node_addon,
    ).serialized_node_settings
    return {'result': result}, http.OK


@decorators.must_have_permission('write')
@decorators.must_have_addon('dataverse', 'user')
@decorators.must_have_addon('dataverse', 'node')
def dataverse_get_datasets(node_addon, **kwargs):
    """Get list of datasets from provided Dataverse alias"""
    alias = request.json.get('alias')

    connection = client.connect_from_settings(node_addon)
    dataverse = client.get_dataverse(connection, alias)
    datasets = client.get_datasets(dataverse)
    ret = {
        'alias': alias,  # include alias to verify dataset container
        'datasets': [{'title': dataset.title, 'doi': dataset.doi} for dataset in datasets],
    }
    return ret, http.OK


@decorators.must_have_permission('write')
@decorators.must_have_addon('dataverse', 'user')
@decorators.must_have_addon('dataverse', 'node')
def dataverse_set_config(node_addon, auth, **kwargs):
    """Saves selected Dataverse and dataset to node settings"""

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

    connection = client.connect_from_settings(node_addon)
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
