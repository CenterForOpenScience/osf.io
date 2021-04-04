# -*- coding: utf-8 -*-
import json
from rest_framework import status as http_status
from flask import request
import logging
from future.moves.urllib.parse import urljoin

from . import SHORT_NAME
from framework.exceptions import HTTPError
from website.project.decorators import (
    must_have_addon,
    must_be_valid_project,
    must_have_permission,
)
from website.ember_osf_web.views import use_ember_app
from website import settings as website_settings
from website.util import api_url_for

from .models import BinderHubToken
from . import settings

logger = logging.getLogger(__name__)

def get_deployment():
    return {
        'images': settings.BINDERHUB_DEPLOYMENT_IMAGES,
    }

def get_launcher_endpoint(endpoint):
    endpoint = endpoint.copy()
    if 'image' in endpoint:
        endpoint['imageurl'] = urljoin(
            website_settings.DOMAIN, '/static/addons/binderhub/' + endpoint['image']
        )
    return endpoint

def get_launcher():
    return {
        'endpoints': [get_launcher_endpoint(e) for e in settings.JUPYTERHUB_LAUNCHERS],
    }

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def binderhub_get_config(**kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    return {'binder_url': addon.get_binder_url()}

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def binderhub_set_config(**kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        binder_url = request.json['binder_url']
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    logger.info('binder_url: {}'.format(binder_url))
    addon.set_binder_url(binder_url)
    return {}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def project_binderhub(**kwargs):
    return use_ember_app()

@must_be_valid_project
@must_have_permission('read')
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
    tokens = BinderHubToken.objects.filter(user=auth.user, node=node)
    token = tokens[0] if len(tokens) > 0 else None
    binderhub_token = json.loads(token.binderhub_token) if token is not None and token.binderhub_token else None
    jupyterhub_token = json.loads(token.jupyterhub_token) if token is not None and token.jupyterhub_token else None
    jupyterhub_url = token.jupyterhub_url if token is not None else None
    if jupyterhub_url is not None:
        clients = settings.JUPYTERHUB_OAUTH_CLIENTS
        api_url = clients[jupyterhub_url]['api_url'] if jupyterhub_url in clients else None
        jupyterhub = {
            'url': jupyterhub_url,
            'authorize_url': jupyterhub_authorize_url,
            'token': jupyterhub_token,
            'api_url': api_url,
        }
    else:
        jupyterhub = None
    return {'data': {'id': node._id, 'type': 'binderhub-config',
                     'attributes': {
                         'binderhub': {
                             'url': addon.get_binder_url(),
                             'authorize_url': binderhub_authorize_url,
                             'token': binderhub_token,
                         },
                         'jupyterhub': jupyterhub,
                         'deployment': get_deployment(),
                         'launcher': get_launcher(),
                     }}}
