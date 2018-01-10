# -*- coding: utf-8 -*-
# """Views fo the node settings page."""
import httplib
from flask import request
import logging

from django.core.exceptions import ValidationError
import urllib

from addons.cloudfiles.serializer import CloudFilesSerializer
from addons.base import generic_views
from rackspace import connection
from openstack.exceptions import HttpException
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from osf.models import ExternalAccount

from website.project.decorators import (
    must_have_addon,
    must_have_permission,
    must_be_addon_authorizer,
)


logger = logging.getLogger(__name__)
debug = logger.debug

SHORT_NAME = 'cloudfiles'
FULL_NAME = 'Cloud Files'

cloudfiles_account_list = generic_views.account_list(
    SHORT_NAME,
    CloudFilesSerializer
)

cloudfiles_import_auth = generic_views.import_auth(
    SHORT_NAME,
    CloudFilesSerializer
)


@must_be_logged_in
def cloudfiles_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""
    try:
        secret_key = request.json['secretKey']
        username = request.json['username']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not (secret_key and username):
        return {
            'message': 'All the fields above are required.'
        }, httplib.BAD_REQUEST

    try:
        # Region is required for the client, but arbitrary here.
        conn = connection.Connection(username=username, api_key=secret_key, region='IAD')
        for _ in conn.object_store.containers():  # Checks if has necessary permission
            pass
    except HttpException:
        return {
            'message': 'Unable to access account.\n'
                       'Check to make sure that the above credentials are valid, '
                       'and that they have permission to list containers.'
        }, httplib.BAD_REQUEST

    try:
        account = ExternalAccount(
            provider=SHORT_NAME,
            provider_name=FULL_NAME,
            oauth_secret=secret_key,
            provider_id=username,
            display_name=username,
        )
        account.save()
    except ValidationError:
        # ... or get the old one
        account = ExternalAccount.objects.get(
            provider=SHORT_NAME,
            provider_id=username
        )
        if account.oauth_key != username or account.oauth_secret != secret_key:
            account.oauth_secret = secret_key
            account.provider_id = username
            account.save()

    assert account is not None

    if not auth.user.external_accounts.filter(id=account.id).exists():
        auth.user.external_accounts.add(account)

    # Ensure Cloud Files is enabled.
    auth.user.get_or_add_addon('cloudfiles', auth=auth)
    auth.user.save()

    return {}


@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def cloudfiles_folder_list(node_addon, **kwargs):
    """ Returns all containers.
    """
    try:
        region = request.args['region']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    return node_addon.get_containers(region)

cloudfiles_get_config = generic_views.get_config(
    SHORT_NAME,
    CloudFilesSerializer
)


def _set_folder(node_addon, folder, auth):
    region = request.json['selectedRegion']
    node_addon.set_folder(folder['id'], region, auth=auth)


cloudfiles_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    CloudFilesSerializer,
    _set_folder
)


cloudfiles_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)


@must_be_addon_authorizer(SHORT_NAME)
@must_have_addon(SHORT_NAME, 'node')
@must_have_permission('write')
def cloudfiles_create_container(auth, node_addon, **kwargs):
    container_name = request.json.get('container_name', '')
    container_location = request.json.get('container_location', '')

    if not container_name:
        return {
            'message': 'Cloud Files container name must contain characters'
        }, httplib.BAD_REQUEST

    if any([char for char in node_addon.FORBIDDEN_CHARS_FOR_CONTAINER_NAMES
            if char in container_name]):
        return {
            'message': 'Cloud Files container name cannot contain either of the characters: / or ?'
        }, httplib.BAD_REQUEST

    try:
        conn = connection.Connection(username=node_addon.external_account.provider_id,
                                     api_key=node_addon.external_account.oauth_secret,
                                     region=container_location)
        encoded_name = urllib.quote_plus(container_name.encode('utf8'))
        conn.object_store.create_container(name=encoded_name)
    except HttpException:
        return {
            'message': ('Unable to access account.\n'
                        'Check to make sure that the above credentials are valid, '
                        'and that they have permission to create containers.')
        }, httplib.BAD_REQUEST

    return {}
