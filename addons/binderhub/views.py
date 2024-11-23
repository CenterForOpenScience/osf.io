# -*- coding: utf-8 -*-
import json
from rest_framework import status as http_status
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from flask import request
import logging
from future.moves.urllib.parse import urljoin, urlencode

from . import SHORT_NAME
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError
from osf.utils.permissions import READ, ADMIN
from website.project.decorators import (
    must_have_addon,
    must_be_valid_project,
    must_have_permission,
    must_be_contributor,
)
from website.ember_osf_web.views import use_ember_app
from website.util import api_url_for
from admin.rdm_addons.decorators import must_be_rdm_addons_allowed

from .models import BinderHubToken, ServerAnnotation, get_default_binderhub, fill_binderhub_secrets
from . import settings

logger = logging.getLogger(__name__)

def _get_jupyterhub_logout_url(binderhubs):
    if len(binderhubs) == 0:
        return None
    binderhub = binderhubs[0]
    if 'jupyterhub_logout_url' in binderhub and binderhub['jupyterhub_logout_url']:
        return binderhub['jupyterhub_logout_url']
    return urljoin(binderhub['jupyterhub_url'], 'hub/logout')

def get_deployment():
    return {
        'images': settings.BINDERHUB_DEPLOYMENT_IMAGES,
    }

@must_be_logged_in
@must_be_rdm_addons_allowed(SHORT_NAME)
def binderhub_get_user_config(auth, **kwargs):
    addon = auth.user.get_addon(SHORT_NAME)
    return {
        'binderhubs': addon.get_binderhubs(allow_secrets=True) if addon else [],
    }

@must_be_logged_in
@must_be_rdm_addons_allowed(SHORT_NAME)
def binderhub_set_user_config(auth, **kwargs):
    addon = auth.user.get_addon(SHORT_NAME)
    if not addon:
        auth.user.add_addon(SHORT_NAME)
        addon = auth.user.get_addon(SHORT_NAME)
    try:
        binderhubs = request.json['binderhubs']
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    addon.set_binderhubs(binderhubs)
    return {}

@must_be_logged_in
@must_be_rdm_addons_allowed(SHORT_NAME)
def purge_binderhub_from_user(auth, **kwargs):
    try:
        auth.user.get_addon(SHORT_NAME).remove_binderhub(
            request.json['url']
        )
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    return {}

@must_be_logged_in
@must_be_rdm_addons_allowed(SHORT_NAME)
def binderhub_add_user_config(auth, **kwargs):
    addon = auth.user.get_addon(SHORT_NAME)
    if not addon:
        auth.user.add_addon(SHORT_NAME)
        addon = auth.user.get_addon(SHORT_NAME)
    try:
        binderhub = request.json['binderhub']
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    binderhubs = [x for x in addon.get_binderhubs(allow_secrets=True) if x['binderhub_url'] != binderhub['binderhub_url']]
    addon.set_binderhubs(binderhubs + [binderhub])
    return {}

@must_be_valid_project
@must_have_permission(ADMIN)
@must_have_addon(SHORT_NAME, 'node')
def binderhub_get_config(**kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    auth = kwargs['auth']
    user_addon = auth.user.get_addon(SHORT_NAME)
    user_binderhubs = []
    if user_addon:
        user_binderhubs = user_addon.get_binderhubs(allow_secrets=False)
    return {
        'binder_url': addon.get_binder_url(),
        'available_binderhubs': addon.get_available_binderhubs(allow_secrets=False),
        'user_binderhubs': user_binderhubs,
        'system_binderhubs': [get_default_binderhub(allow_secrets=False)],
    }

@must_be_valid_project
@must_have_permission(ADMIN)
@must_have_addon(SHORT_NAME, 'node')
def binderhub_set_config(**kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        binder_url = request.json['binder_url']
        available_binderhubs = request.json['available_binderhubs']
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    logger.info('binder_url: {}'.format(binder_url))
    # fill secrets
    old_binderhubs = addon.get_available_binderhubs(allow_secrets=True)
    auth = kwargs['auth']
    user_addon = auth.user.get_addon(SHORT_NAME)
    user_binderhubs = []
    if user_addon:
        user_binderhubs = user_addon.get_binderhubs(allow_secrets=True)
    available_binderhubs = fill_binderhub_secrets(
        available_binderhubs,
        [
            old_binderhubs,
            user_binderhubs,
            [get_default_binderhub(allow_secrets=True)]
        ]
    )
    addon.set_binder_url(binder_url)
    addon.set_available_binderhubs(available_binderhubs)
    return {}

@must_be_valid_project
@must_have_permission(ADMIN)
@must_have_addon(SHORT_NAME, 'node')
def delete_binderhub(**kwargs):
    try:
        target_url = request.json['url']
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    (
        kwargs['node'] or kwargs['project']
    ).get_addon(SHORT_NAME).remove_binderhub(target_url)
    ServerAnnotation.objects.filter(binderhub_url=target_url).delete()
    return {}

@must_be_valid_project
@must_be_contributor
@must_have_addon(SHORT_NAME, 'node')
def project_binderhub(**kwargs):
    return use_ember_app()

@must_be_valid_project
@must_have_permission(READ)
@must_have_addon(SHORT_NAME, 'node')
def binderhub_logout(**kwargs):
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    addon = node.get_addon(SHORT_NAME)
    default_binderhub_url = addon.get_binder_url()
    binderhub_url = request.args.get('binderhub_url', default_binderhub_url)
    tokens = BinderHubToken.objects.filter(user=auth.user, node=node, binderhub_url=binderhub_url)
    user_addon = auth.user.get_addon(SHORT_NAME)
    node_binderhubs = addon.get_available_binderhubs(allow_secrets=False)
    user_binderhubs = []
    if user_addon:
        user_binderhubs = user_addon.get_binderhubs(allow_secrets=False)
    default_binderhub_url = addon.get_binder_url()
    all_binderhubs = node_binderhubs + user_binderhubs
    binderhubs = [b for b in all_binderhubs if b['binderhub_url'] == binderhub_url]
    if len(tokens) == 0:
        return {
            'data': {
                'deleted': 0,
                'jupyterhub_logout_url': _get_jupyterhub_logout_url(binderhubs),
            },
        }
    token = tokens[0]
    token.binderhub_token = None
    token.jupyterhub_token = None
    token.save()
    return {
        'data': {
            'deleted': 1,
            'jupyterhub_logout_url': _get_jupyterhub_logout_url(binderhubs),
        },
    }


@must_be_valid_project
@must_have_permission(READ)
@must_have_addon(SHORT_NAME, 'node')
def binderhub_get_config_ember(**kwargs):
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    addon = node.get_addon(SHORT_NAME)
    binderhub_authorize_url = api_url_for('binderhub_oauth_authorize',
                                          pid=node._id,
                                          serviceid='binderhub',
                                          _absolute=True)
    jupyterhub_authorize_url = api_url_for('binderhub_oauth_authorize',
                                           pid=node._id,
                                           serviceid='jupyterhub',
                                           _absolute=True)
    jupyterhub_logout_url = api_url_for('binderhub_logout',
                                        pid=node._id,
                                        _absolute=True)
    user_addon = auth.user.get_addon(SHORT_NAME)
    node_binderhubs = addon.get_available_binderhubs(allow_secrets=False)
    user_binderhubs = []
    if user_addon:
        user_binderhubs = user_addon.get_binderhubs(allow_secrets=False)
    default_binderhub_url = addon.get_binder_url()
    all_binderhubs = node_binderhubs + user_binderhubs
    binderhub_urls = []
    binderhubs = []
    for binderhub in all_binderhubs:
        binderhub_url = binderhub['binderhub_url']
        if binderhub_url in binderhub_urls:
            continue
        tokens = BinderHubToken.objects.filter(user=auth.user, node=node, binderhub_url=binderhub_url)
        token = tokens[0] if len(tokens) > 0 else None
        binderhub_token = json.loads(token.binderhub_token) if token is not None and token.binderhub_token else None
        jupyterhub_url = token.jupyterhub_url if token is not None else None
        authorize_url = None
        if binderhub['binderhub_oauth_client_id'] is not None:
            authorize_url = binderhub_authorize_url + '?' + urlencode({
                'binderhub_url': binderhub_url,
            })
        else:
            jupyterhub_url = binderhub['jupyterhub_url']
        binderhubs.append({
            'default': default_binderhub_url == binderhub_url,
            'url': binderhub_url,
            'authorize_url': authorize_url,
            'token': binderhub_token,
            'jupyterhub_url': jupyterhub_url,
        })
        binderhub_urls.append(binderhub_url)
    jupyterhubs = []
    jupyterhub_urls = []
    for binderhub in all_binderhubs:
        binderhub_url = binderhub['binderhub_url']
        tokens = BinderHubToken.objects.filter(user=auth.user, node=node, binderhub_url=binderhub_url)
        token = tokens[0] if len(tokens) > 0 else None
        jupyterhub_token = json.loads(token.jupyterhub_token) if token is not None and token.jupyterhub_token else None
        jupyterhub_url = token.jupyterhub_url if token is not None else None
        if binderhub['jupyterhub_oauth_client_id'] is None:
            jupyterhub_url = binderhub['jupyterhub_url']
        if jupyterhub_url is None or jupyterhub_url in jupyterhub_urls:
            continue
        api_url = binderhub['jupyterhub_api_url']
        authorize_url = None
        logout_url = None
        if binderhub['jupyterhub_oauth_client_id'] is not None:
            authorize_url = jupyterhub_authorize_url + '?' + urlencode({
                'binderhub_url': binderhub_url,
            })
            logout_url = jupyterhub_logout_url + '?' + urlencode({
                'binderhub_url': binderhub_url,
            })
        jupyterhubs.append({
            'url': jupyterhub_url,
            'authorize_url': authorize_url,
            'token': jupyterhub_token,
            'api_url': api_url,
            'logout_url': logout_url,
            'max_servers': binderhub['jupyterhub_max_servers'] if 'jupyterhub_max_servers' in binderhub else None,
        })
        jupyterhub_urls.append(jupyterhub_url)
    return {'data': {'id': node._id, 'type': 'binderhub-config',
                     'attributes': {
                         'binderhubs': binderhubs,
                         'jupyterhubs': jupyterhubs,
                         'deployment': get_deployment(),
                         'node_binderhubs': node_binderhubs,
                         'user_binderhubs': user_binderhubs,
                         'mpm_releases': settings.MATLAB_RELEASES,
                     }}}

@must_be_valid_project
@must_have_permission(READ)
@must_have_addon(SHORT_NAME, 'node')
def get_matlab_product_name_list(**kwargs):
    try:
        return {
            'data': {
                'type': 'matlab-product-name-list',
                'id': kwargs['release'],
                'attributes': {
                    'release': kwargs['release'],
                    'names': settings.MATLAB_PRODUCTNAMES_MAP[kwargs['release']],
                }
            }
        }
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

@must_be_valid_project
@must_have_permission(READ)
@must_have_addon(SHORT_NAME, 'node')
def get_server_annotation(**kwargs):
    try:
        annotations = ServerAnnotation.objects.filter(
            user=kwargs['auth'].user,
            node=kwargs['node'] or kwargs['project'],
        )
        return {
            'data': [annot.make_resource_object() for annot in annotations]
        }
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

@must_be_valid_project
@must_have_permission(READ)
@must_have_addon(SHORT_NAME, 'node')
def create_server_annotation(**kwargs):
    try:
        attrs = request.json['data']['attributes']
        if ServerAnnotation.objects.filter(
            user=kwargs['auth'].user,
            node=kwargs['node'] or kwargs['project'],
            binderhub_url=attrs['binderhubUrl'],
            jupyterhub_url=attrs['jupyterhubUrl'],
            server_url=attrs['serverUrl'],
        ).exists():
            raise HTTPError(
                http_status.HTTP_409_CONFLICT,
                message='Required server annotation entry already exists.'
            )
        annot = ServerAnnotation(
            user=kwargs['auth'].user,
            node=kwargs['node'] or kwargs['project'],
            binderhub_url=attrs['binderhubUrl'],
            jupyterhub_url=attrs['jupyterhubUrl'],
            server_url=attrs['serverUrl'],
            name=attrs['name'],
            memotext='',
        )
        annot.save()
        return {'data': annot.make_resource_object()}
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

@must_be_valid_project
@must_have_permission(READ)
@must_have_addon(SHORT_NAME, 'node')
def patch_server_annotation(**kwargs):
    try:
        annot = ServerAnnotation.objects.get(
            id=kwargs['aid'],
            user=kwargs['auth'].user,
            node=kwargs['node'] or kwargs['project'],
        )
        annot.memotext = request.json['data']['attributes']['memotext']
        annot.save()
        return {'data': annot.make_resource_object()}
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    except ObjectDoesNotExist:
        raise HTTPError(
            http_status.HTTP_404_NOT_FOUND,
            message=f'ServerAnnotation with id={kwargs["aid"]} not found.'
        )
    except MultipleObjectsReturned:
        raise HTTPError(
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f'Multiple ServerAnnotations have id={kwargs["aid"]}.'
        )

@must_be_valid_project
@must_have_permission(READ)
@must_have_addon(SHORT_NAME, 'node')
def delete_server_annotation(**kwargs):
    try:
        ServerAnnotation.objects.get(
            id=kwargs['aid'],
            user=kwargs['auth'].user,
            node=kwargs['node'] or kwargs['project'],
        ).delete()
    except ObjectDoesNotExist:
        raise HTTPError(
            http_status.HTTP_404_NOT_FOUND,
            message=f'ServerAnnotation with id={kwargs["aid"]} not found.'
        )
    except MultipleObjectsReturned:
        raise HTTPError(
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f'Multiple ServerAnnotations have id={kwargs["aid"]}.'
        )
    else:
        return {
            'data': {
                'type': 'server-annotation',
                'id': kwargs['aid'],
            }
        }
