import httplib

from swiftclient import exceptions as swift_exceptions
from flask import request
from django.core.exceptions import ValidationError

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from addons.base import generic_views
from addons.swift import utils
from addons.swift.provider import SwiftProvider, to_auth_desc
from addons.swift.serializer import SwiftSerializer
from osf.models import ExternalAccount
from website.project.decorators import (
    must_have_addon, must_have_permission,
    must_be_addon_authorizer,
)

SHORT_NAME = 'swift'
FULL_NAME = 'OpenStack Swift'

swift_account_list = generic_views.account_list(
    SHORT_NAME,
    SwiftSerializer
)

swift_import_auth = generic_views.import_auth(
    SHORT_NAME,
    SwiftSerializer
)

swift_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

swift_get_config = generic_views.get_config(
    SHORT_NAME,
    SwiftSerializer
)

def _set_folder(node_addon, folder, auth):
    folder_id = folder['id']
    node_addon.set_folder(folder_id, auth=auth)
    node_addon.save()

swift_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    SwiftSerializer,
    _set_folder
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def swift_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
    """
    return node_addon.get_folders()

@must_be_logged_in
def swift_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""
    try:
        auth_version = request.json['auth_version']
        auth_url = request.json['auth_url']
        access_key = request.json['access_key']
        secret_key = request.json['secret_key']
        tenant_name = request.json['tenant_name']
        if auth_version == '3':
            user_domain_name = request.json['user_domain_name']
            project_domain_name = request.json['project_domain_name']
        else:
            user_domain_name = None
            project_domain_name = None
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not (auth_version and auth_url and access_key and secret_key and tenant_name):
        return {
            'message': 'All the fields above are required.'
        }, httplib.BAD_REQUEST
    if auth_version == '3' and not user_domain_name:
        return {
            'message': 'The field `user_domain_name` is required when you choose identity V3.'
        }, httplib.BAD_REQUEST
    if auth_version == '3' and not project_domain_name:
        return {
            'message': 'The field `project_domain_name` is required when you choose identity V3.'
        }, httplib.BAD_REQUEST

    user_info = utils.get_user_info(auth_version, auth_url, access_key,
                                    user_domain_name, secret_key, tenant_name,
                                    project_domain_name)
    if not user_info:
        return {
            'message': ('Unable to access account.\n'
                'Check to make sure that the above credentials are valid, '
                'and that they have permission to list containers.')
        }, httplib.BAD_REQUEST

    if not utils.can_list(auth_version, auth_url, access_key, user_domain_name,
                          secret_key, tenant_name, project_domain_name):
        return {
            'message': ('Unable to list containers.\n'
                'Listing containers is required permission.')
        }, httplib.BAD_REQUEST

    provider = SwiftProvider(account=None, auth_version=auth_version,
                             auth_url=auth_url, tenant_name=tenant_name,
                             project_domain_name=project_domain_name,
                             username=access_key,
                             user_domain_name=user_domain_name,
                             password=secret_key)
    try:
        provider.account.save()
    except ValidationError:
        # ... or get the old one
        provider.account = ExternalAccount.objects.get(
            provider=SHORT_NAME,
            provider_id='{}:{}'.format(to_auth_desc(auth_version, auth_url,
                                                    user_domain_name,
                                                    tenant_name,
                                                    project_domain_name),
                                       access_key).lower()
        )
        if provider.account.oauth_key != secret_key:
            provider.account.oauth_key = secret_key
            provider.account.save()
    assert provider.account is not None

    if not auth.user.external_accounts.filter(id=provider.account.id).exists():
        auth.user.external_accounts.add(provider.account)

    # Ensure Swift is enabled.
    auth.user.get_or_add_addon('swift', auth=auth)
    auth.user.save()

    return {}


@must_be_addon_authorizer(SHORT_NAME)
@must_have_addon('swift', 'node')
@must_have_permission('write')
def swift_create_container(auth, node_addon, **kwargs):
    container_name = request.json.get('container_name', '')

    if not utils.validate_container_name(container_name):
        return {
            'message': 'That container name is not valid.',
            'title': 'Invalid container name',
        }, httplib.BAD_REQUEST

    try:
        utils.create_container(node_addon, container_name)
    except swift_exceptions.ClientException as e:
        return {
            'message': e.message,
            'title': "Problem creating container '{0}'".format(container_name),
        }, httplib.BAD_REQUEST

    return {}
