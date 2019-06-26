"""Views for the node settings page."""
# -*- coding: utf-8 -*-
from rest_framework import status as http_status

from django.utils import timezone
from django.core.exceptions import ValidationError
from requests.exceptions import SSLError
from flask import request

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from addons.base import generic_views
from addons.dataverse import client
from addons.dataverse.models import DataverseProvider
from addons.dataverse.settings import DEFAULT_HOSTS
from addons.dataverse.serializer import DataverseSerializer
from dataverse.exceptions import VersionJsonNotFoundError, OperationFailedError
from osf.models import ExternalAccount
from osf.utils.permissions import WRITE
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_contributor_or_public
)
from website.util import rubeus, api_url_for

SHORT_NAME = 'dataverse'
FULL_NAME = 'Dataverse'

dataverse_account_list = generic_views.account_list(
    SHORT_NAME,
    DataverseSerializer
)

dataverse_import_auth = generic_views.import_auth(
    SHORT_NAME,
    DataverseSerializer
)

dataverse_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

dataverse_get_config = generic_views.get_config(
    SHORT_NAME,
    DataverseSerializer
)

## Auth ##

@must_be_logged_in
def dataverse_user_config_get(auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Dataverse user settings.
    """

    user_addon = auth.user.get_addon('dataverse')
    user_has_auth = False
    if user_addon:
        user_has_auth = user_addon.has_auth

    return {
        'result': {
            'userHasAuth': user_has_auth,
            'urls': {
                'create': api_url_for('dataverse_add_user_account'),
                'accounts': api_url_for('dataverse_account_list'),
            },
            'hosts': DEFAULT_HOSTS,
        },
    }, http_status.HTTP_200_OK


## Config ##

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
    except ValidationError:
        # ... or get the old one
        provider.account = ExternalAccount.objects.get(
            provider=provider.short_name,
            provider_id=api_token
        )

    if not user.external_accounts.filter(id=provider.account.id).exists():
        user.external_accounts.add(provider.account)

    user_addon = auth.user.get_addon('dataverse')
    if not user_addon:
        user.add_addon('dataverse')
    user.save()

    # Need to ensure that the user has dataverse enabled at this point
    user.get_or_add_addon('dataverse', auth=auth)
    user.save()

    return {}

@must_have_permission(WRITE)
@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def dataverse_set_config(node_addon, auth, **kwargs):
    """Saves selected Dataverse and dataset to node settings"""

    user_settings = node_addon.user_settings
    user = auth.user

    if user_settings and user_settings.owner != user:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    alias = request.json.get('dataverse', {}).get('alias')
    doi = request.json.get('dataset', {}).get('doi')

    if doi is None or alias is None:
        return HTTPError(http_status.HTTP_400_BAD_REQUEST)

    connection = client.connect_from_settings(node_addon)
    dataverse = client.get_dataverse(connection, alias)
    dataset = client.get_dataset(dataverse, doi)

    node_addon.set_folder(dataverse, dataset, auth)

    return {'dataverse': dataverse.title, 'dataset': dataset.title}, http_status.HTTP_200_OK


@must_have_permission(WRITE)
@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
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
    return ret, http_status.HTTP_200_OK

## Crud ##


@must_have_permission(WRITE)
@must_not_be_registration
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def dataverse_publish_dataset(node_addon, auth, **kwargs):
    node = node_addon.owner
    publish_both = request.json.get('publish_both', False)

    now = timezone.now()

    connection = client.connect_from_settings_or_401(node_addon)

    dataverse = client.get_dataverse(connection, node_addon.dataverse_alias)
    dataset = client.get_dataset(dataverse, node_addon.dataset_doi)

    if publish_both:
        client.publish_dataverse(dataverse)
    client.publish_dataset(dataset)

    # Add a log
    node.add_log(
        action='dataverse_dataset_published',
        params={
            'project': node.parent_id,
            'node': node._id,
            'dataset': dataset.title,
        },
        auth=auth,
        log_date=now,
    )

    return {'dataset': dataset.title}, http_status.HTTP_200_OK

## HGRID ##

def _dataverse_root_folder(node_addon, auth, **kwargs):
    node = node_addon.owner

    default_version = 'latest-published'
    version = 'latest-published' if not node.can_edit(auth) else default_version

    # Quit if no dataset linked
    if not node_addon.complete:
        return []

    can_edit = node.can_edit(auth)

    permissions = {
        'edit': can_edit and not node.is_registration,
        'view': node.can_view(auth)
    }

    try:
        connection = client.connect_from_settings(node_addon)
        dataverse = client.get_dataverse(connection, node_addon.dataverse_alias)
        dataset = client.get_dataset(dataverse, node_addon.dataset_doi)
    except SSLError:
        return [rubeus.build_addon_root(
            node_addon,
            node_addon.dataset,
            permissions=permissions,
            private_key=kwargs.get('view_only', None),
        )]

    # Quit if doi does not produce a dataset
    if dataset is None:
        return []

    published_files = client.get_files(dataset, published=True)

    # Produce draft version or quit if no published version is available
    if not published_files:
        if can_edit:
            version = 'latest'
        else:
            return []

    urls = {
        'publish': node.api_url_for('dataverse_publish_dataset'),
    }

    # determine if there are any changes between the published and draft
    # versions of the dataset
    try:
        dataset.get_metadata('latest-published')
        dataset_is_published = True
        dataset_draft_modified = dataset.get_state() == 'DRAFT'
    except VersionJsonNotFoundError:
        dataset_is_published = False
        dataset_draft_modified = True

    # Get the dataverse host
    # (stored in oauth_key because dataverse doesn't use that)
    dataverse_host = node_addon.external_account.oauth_key

    try:
        host_custom_publish_text = client.get_custom_publish_text(connection)
    except OperationFailedError:
        host_custom_publish_text = ''

    return [rubeus.build_addon_root(
        node_addon,
        node_addon.dataset,
        urls=urls,
        permissions=permissions,
        dataset=node_addon.dataset,
        doi=dataset.doi,
        dataverse=dataverse.title,
        hasPublishedFiles=bool(published_files),
        dataverseIsPublished=dataverse.is_published,
        datasetIsPublished=dataset_is_published,
        datasetDraftModified=dataset_draft_modified,
        version=version,
        host=dataverse_host,
        hostCustomPublishText=host_custom_publish_text,
        private_key=kwargs.get('view_only', None),
    )]


@must_be_contributor_or_public
@must_have_addon(SHORT_NAME, 'node')
def dataverse_root_folder(node_addon, auth, **kwargs):
    return _dataverse_root_folder(node_addon, auth=auth)


@must_be_contributor_or_public
@must_have_addon(SHORT_NAME, 'node')
def dataverse_get_widget_contents(node_addon, **kwargs):

    data = {
        'connected': False,
    }

    if not node_addon.complete:
        return {'data': data}, http_status.HTTP_200_OK

    doi = node_addon.dataset_doi
    alias = node_addon.dataverse_alias

    connection = client.connect_from_settings_or_401(node_addon)
    dataverse = client.get_dataverse(connection, alias)
    dataset = client.get_dataset(dataverse, doi)

    if dataset is None:
        return {'data': data}, http_status.HTTP_400_BAD_REQUEST

    dataverse_host = node_addon.external_account.oauth_key
    dataverse_url = 'http://{0}/dataverse/{1}'.format(dataverse_host, alias)
    dataset_url = 'https://doi.org/' + doi

    data.update({
        'connected': True,
        'dataverse': node_addon.dataverse,
        'dataverseUrl': dataverse_url,
        'dataset': node_addon.dataset,
        'doi': doi,
        'datasetUrl': dataset_url,
        'citation': dataset.citation,
    })
    return {'data': data}, http_status.HTTP_200_OK
