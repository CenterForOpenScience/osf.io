"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import httplib as http

from flask import request, send_file
import StringIO

from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website.addons.base import generic_views
from website.addons.dmptool import client
from website.addons.dmptool.model import DmptoolProvider
from website.addons.dmptool.settings import DEFAULT_HOSTS
from website.addons.dmptool.serializer import DmptoolSerializer
from website.oauth.models import ExternalAccount
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission,
    must_be_contributor_or_public
)
from website.util import api_url_for
from website.util.sanitize import assert_clean

SHORT_NAME = 'dmptool'
FULL_NAME = 'Dmptool'

dmptool_account_list = generic_views.account_list(
    SHORT_NAME,
    DmptoolSerializer
)

dmptool_import_auth = generic_views.import_auth(
    SHORT_NAME,
    DmptoolSerializer
)

dmptool_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

dmptool_get_config = generic_views.get_config(
    SHORT_NAME,
    DmptoolSerializer
)

dmptool_root_folder = generic_views.root_folder(
    SHORT_NAME
)

## Auth ##

@must_be_logged_in
def dmptool_user_config_get(auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Dmptool user settings.
    """

    user_addon = auth.user.get_addon('dmptool')
    user_has_auth = False
    if user_addon:
        user_has_auth = user_addon.has_auth

    return {
        'result': {
            'userHasAuth': user_has_auth,
            'urls': {
                'create': api_url_for('dmptool_add_user_account'),
                'accounts': api_url_for('dmptool_account_list'),
            },
            'hosts': DEFAULT_HOSTS,
        },
    }, http.OK


## Config ##

@must_be_logged_in
def dmptool_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""
    user = auth.user
    provider = DmptoolProvider()

    host = request.json.get('host').rstrip('/')
    api_token = request.json.get('api_token')

    # Verify that credentials are valid
    client.connect_or_error(host, api_token)

    # Note: `DmptoolSerializer` expects display_name to be a URL
    try:
        provider.account = ExternalAccount(
            provider=provider.short_name,
            provider_name=provider.name,
            display_name=host,       # no username; show host
            oauth_key=host,          # hijacked; now host
            oauth_secret=api_token,  # hijacked; now api_token
            provider_id=api_token,   # Change to username if Dmptool allows
        )
        provider.account.save()
    except KeyExistsException:
        # ... or get the old one
        provider.account = ExternalAccount.find_one(
            Q('provider', 'eq', provider.short_name) &
            Q('provider_id', 'eq', api_token)
        )

    if provider.account not in user.external_accounts:
        user.external_accounts.append(provider.account)

    user_addon = auth.user.get_addon('dmptool')
    if not user_addon:
        user.add_addon('dmptool')
    user.save()

    # Need to ensure that the user has dmptool enabled at this point
    user.get_or_add_addon('dmptool', auth=auth)
    user.save()

    return {}

@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def dmptool_set_config(node_addon, auth, **kwargs):
    """Saves selected Dmptool and dataset to node settings"""

    user_settings = node_addon.user_settings
    user = auth.user

    if user_settings and user_settings.owner != user:
        raise HTTPError(http.FORBIDDEN)

    try:
        assert_clean(request.json)
    except AssertionError:
        # TODO: Test me!
        raise HTTPError(http.NOT_ACCEPTABLE)

    alias = request.json.get('dmptool', {}).get('alias')
    doi = request.json.get('dataset', {}).get('doi')

    if doi is None or alias is None:
        return HTTPError(http.BAD_REQUEST)

    connection = client.connect_from_settings(node_addon)
    dmptool = client.get_dmptool(connection, alias)
    dataset = client.get_dataset(dmptool, doi)

    node_addon.set_folder(dmptool, dataset, auth)

    return {'dmptool': dmptool.title, 'dataset': dataset.title}, http.OK

## Crud ##

## Widget ##

# @must_be_contributor_or_public
# @must_have_addon(SHORT_NAME, 'node')
# def dmptool_widget(node_addon, **kwargs):

#     node = node_addon.owner
#     widget_url = node.api_url_for('dmptool_get_widget_contents')

#     ret = {
#         'complete': node_addon.complete,
#         'widget_url': widget_url,
#     }
#     ret.update(node_addon.config.to_json())

#     return ret, http.OK


# @must_be_contributor_or_public
# @must_have_addon(SHORT_NAME, 'node')
# def dmptool_get_widget_contents(node_addon, **kwargs):

#     node = node_addon.owner
#     data = {
#         'connected': False,
#     }

#     if not node_addon.complete:
#         return {'data': data}, http.OK

#     connection = client.connect_from_settings_or_401(node_addon)
#     plans = connection.plans_owned()
#     dmptool_host = node_addon.external_account.oauth_key

#     # loop through plans to add plan url to each plan
#     # https://dmptool.org/plans/21222/edit
#     for plan in plans:
#         plan['url'] = 'https://{}/plans/{}/edit'.format(dmptool_host, plan['id'])
#         plan['get_plan_url'] = node.api_url_for('dmptool_get_plan',
#                 planid=plan['id'])

#     data.update({
#         'dmptool_host': dmptool_host,
#         'plans': plans,
#         'connected': True,
#         'urls': {
#             'add_user_account': api_url_for('dmptool_add_user_account')
#         }
#     })
#     return {'data': data}, http.OK


# @must_have_addon(SHORT_NAME, 'user')
# @must_have_addon(SHORT_NAME, 'node')
# def dmptool_get_plan(node_addon, planid, **kwargs):
#     """Get plan for id"""

#     node = node_addon.owner
#     connection = client.connect_from_settings_or_401(node_addon)
#     try:
#         plan = connection.plans_full(id_=planid)
#         plan['pdf_url'] = node.api_url_for('dmptool_download_plan',
#             planid=plan['id'], fmt='pdf')
#         plan['docx_url'] = node.api_url_for('dmptool_download_plan',
#             planid=plan['id'], fmt='docx')
#         html_ = 'HTML to come'
#     except:
#         plan = None
#         html_ = None

#     ret = {
#         'planid': planid,
#         'plan': plan,
#         'html': html_
#     }
#     return ret, http.OK

# @must_have_addon(SHORT_NAME, 'user')
# @must_have_addon(SHORT_NAME, 'node')
# def dmptool_download_plan(node_addon, planid, fmt, **kwargs):
#     # http://flask.pocoo.org/snippets/32/

#     connection = client.connect_from_settings_or_401(node_addon)

#     strIO = StringIO.StringIO()
#     strIO.write(connection.plans_full(planid, fmt))
#     strIO.seek(0)
#     return send_file(strIO,
#                      attachment_filename='{}.{}'.format(planid, fmt),
#                      as_attachment=True)
