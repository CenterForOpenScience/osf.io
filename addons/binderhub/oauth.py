# -*- coding: utf-8 -*-
import json
from rest_framework import status as http_status
from flask import request
from flask import redirect
import logging
import requests
from future.moves.urllib.parse import urljoin, urlencode

from osf.models.node import AbstractNode
from framework.sessions import session
from framework.exceptions import HTTPError
from framework.exceptions import PermissionsError
from website.util import api_url_for, web_url_for
from website.project.decorators import (
    must_have_addon,
    must_be_valid_project,
    must_have_permission,
)
from framework.auth.decorators import must_be_logged_in
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import MissingTokenError
from requests.exceptions import HTTPError as RequestsHTTPError
from .models import BinderHubToken, get_default_binderhubs
from . import SHORT_NAME
from . import settings

logger = logging.getLogger(__name__)

def get_client_settings(service_id, binderhub_url, auth, node):
    if service_id == 'binderhub':
        client_settings = _find_binderhub_by_url(binderhub_url, auth, node)
        if client_settings is None:
            logger.error('Unexpected BinderHub: {}'.format(binderhub_url))
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    else:
        tokens = BinderHubToken.objects.filter(user=auth.user, node=node, binderhub_url=binderhub_url)
        if len(tokens) == 0:
            logger.error('Not logged in to BinderHub')
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        token = tokens[0]
        client_settings = _find_jupyterhub_by_url(token.jupyterhub_url, auth, node)
        if client_settings is None:
            logger.error('Unexpected JupyterHub: {}'.format(token.jupyterhub_url))
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    return client_settings


def _equals_url(url1, url2):
    return _normalize_url(url1) == _normalize_url(url2)


def _normalize_url(url):
    if not url.endswith('/'):
        return url
    return url[:-1]


def _get_oauth_client(prefix, binderhub, mapping):
    return dict([(k[len(prefix):] if k not in mapping else mapping[k], v)
                 for k, v in binderhub.items()
                 if k.startswith(prefix) or k in mapping])


def _find_binderhub_by_url(binderhub_url, auth, node):
    for binderhub in _get_all_binderhubs(auth, node):
        if _equals_url(binderhub['binderhub_url'], binderhub_url):
            return _get_oauth_client('binderhub_oauth_', binderhub, {
                'binderhub_services_url': 'services_url',
            })
    return None


def _find_jupyterhub_by_url(jupyterhub_url, auth, node):
    for binderhub in _get_all_binderhubs(auth, node):
        if _equals_url(binderhub['jupyterhub_url'], jupyterhub_url):
            return _get_oauth_client('jupyterhub_oauth_', binderhub, {
                'jupyterhub_api_url': 'api_url',
                'jupyterhub_admin_api_token': 'admin_api_token',
            })
    clients = settings.JUPYTERHUB_OAUTH_CLIENTS
    if jupyterhub_url in clients:
        return clients[jupyterhub_url]
    return None


def _get_all_binderhubs(auth, node):
    addon = node.get_addon(SHORT_NAME)
    user_addon = auth.user.get_addon(SHORT_NAME)
    node_binderhubs = addon.get_available_binderhubs(allow_secrets=True)
    user_binderhubs = []
    if user_addon:
        user_binderhubs = user_addon.get_binderhubs(allow_secrets=True)
    system_binderhubs = get_default_binderhubs(allow_secrets=True)
    return node_binderhubs + user_binderhubs + system_binderhubs

def update_binderhub_data(client_settings, token, token_resp):
    token.binderhub_token = json.dumps(token_resp)
    auth_headers = {
        'Authorization': '{} {}'.format(token_resp['token_type'],
                                        token_resp['access_token']),
    }
    services_resp = requests.get(client_settings['services_url'],
                                 headers=auth_headers)
    if not services_resp.ok:
        logger.error('Retrieve Services status_code={}, body={}'.format(
            services_resp.status_code,
            services_resp.text
        ))
        raise HTTPError(http_status.HTTP_503_SERVICE_UNAVAILABLE)
    services = services_resp.json()
    logger.info('Services {}'.format(services))
    for service in services:
        if service['type'] != 'jupyterhub':
            continue
        token.jupyterhub_url = service['url']


def update_jupyterhub_data(client_settings, token, token_resp):
    id_auth_headers = {
        'Authorization': '{} {}'.format(token_resp['token_type'],
                                        token_resp['access_token']),
    }
    user_resp = requests.get(urljoin(client_settings['api_url'], 'user'),
                             headers=id_auth_headers)
    if not user_resp.ok:
        logger.error('Retrieve User status_code={}, body={}'.format(
            user_resp.status_code,
            user_resp.text
        ))
        raise HTTPError(http_status.HTTP_503_SERVICE_UNAVAILABLE)
    user = user_resp.json()
    if user['kind'] != 'user':
        logger.error('Unexpected kind of User {}'.format(user))
        raise HTTPError(http_status.HTTP_503_SERVICE_UNAVAILABLE)
    logger.info('User {}'.format(user))
    user_name = user['name']
    admin_auth_headers = {
        'Authorization': 'token {}'.format(client_settings['admin_api_token']),
    }
    token_req = {
        'expires_in': settings.JUPYTERHUB_TOKEN_EXPIRES_IN_SEC,
        'note': 'RDM BinderHub Addon',
    }
    token_resp = requests.post(urljoin(client_settings['api_url'],
                                      'users/{}/tokens'.format(user_name)),
                               headers=admin_auth_headers,
                               json=token_req)
    if not token_resp.ok:
        logger.error('Retrieve Token status_code={}, body={}'.format(
            token_resp.status_code,
            token_resp.text
        ))
        raise HTTPError(http_status.HTTP_503_SERVICE_UNAVAILABLE)
    token_obj = token_resp.json()
    if token_obj['kind'] != 'api_token':
        logger.error('Unexpected kind of Token {}'.format(token_obj))
        raise HTTPError(http_status.HTTP_503_SERVICE_UNAVAILABLE)
    logger.debug('Token {}'.format(token_obj))
    token.jupyterhub_token = json.dumps({
        'user': user_name,
        'token_type': 'Bearer',
        'access_token': token_obj['token'],
        'expires_at': token_obj['expires_at'],
    })


@must_be_valid_project
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def binderhub_oauth_authorize(**kwargs):
    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    service_id = kwargs['serviceid']
    default_binderhub_url = node.get_addon(SHORT_NAME).get_binder_url()
    binderhub_url = request.args.get('binderhub_url', default_binderhub_url)
    context_bh = request.args.get('bh', None)
    context_jh = request.args.get('jh', None)
    # create a dict on the session object if it's not already there
    if session.data.get('oauth_states') is None:
        session.data['oauth_states'] = {}

    client_settings = get_client_settings(service_id, binderhub_url, auth, node)

    # build the URL
    oauth = OAuth2Session(
        client_settings['client_id'],
        redirect_uri=api_url_for('binderhub_oauth_callback', _absolute=True),
        scope=client_settings['scope'],
    )

    if client_settings['authorize_url'] is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    url, state = oauth.authorization_url(client_settings['authorize_url'])

    # save state token to the session for confirmation in the callback
    session.data['oauth_states'][SHORT_NAME] = {
        'state': state,
        'node_id': node._id,
        'service_id': service_id,
        'binderhub_url': binderhub_url,
        'context_bh': context_bh,
        'context_jh': context_jh,
    }

    session.save()
    sep = '&' if '?' in url else '?'
    params = {'return_on_error': node.absolute_url}
    return redirect(url + sep + urlencode(params))


@must_be_logged_in
def binderhub_oauth_callback(**kwargs):
    auth = kwargs['auth']
    # make sure the user has temporary credentials for this provider
    try:
        cached_credentials = session.data['oauth_states'][SHORT_NAME]
    except KeyError:
        raise PermissionsError('OAuth flow not recognized.')
    service_id = cached_credentials['service_id']
    binderhub_url = cached_credentials['binderhub_url']
    node = AbstractNode.objects.get(guids___id=cached_credentials['node_id'])
    client_settings = get_client_settings(service_id, binderhub_url, auth, node)

    state = request.args.get('state')

    # make sure this is the same user that started the flow
    if cached_credentials.get('state') != state:
        raise PermissionsError('Request token does not match')

    try:
        callback_url = api_url_for('binderhub_oauth_callback', _absolute=True)
        response = OAuth2Session(
            client_settings['client_id'],
            redirect_uri=callback_url,
        ).fetch_token(
            client_settings['token_url'],
            client_secret=client_settings['client_secret'],
            code=request.args.get('code'),
        )
        logger.debug('token: {}'.format(response))

        tokens = BinderHubToken.objects.filter(user=auth.user, node=node, binderhub_url=binderhub_url)
        if len(tokens) > 0:
            token = tokens[0]
        else:
            token = BinderHubToken.objects.create(user=auth.user, node=node, binderhub_url=binderhub_url)
        if service_id == 'binderhub':
            update_binderhub_data(client_settings, token, response)
        else:
            update_jupyterhub_data(client_settings, token, response)
        token.save()
    except (MissingTokenError, RequestsHTTPError):
        raise HTTPError(http_status.HTTP_503_SERVICE_UNAVAILABLE)
    context_params = {}
    if 'context_bh' in cached_credentials and cached_credentials['context_bh'] is not None:
        context_params['bh'] = cached_credentials['context_bh']
    if 'context_jh' in cached_credentials and cached_credentials['context_jh'] is not None:
        context_params['jh'] = cached_credentials['context_jh']
    context_query = '' if len(context_params) == 0 else ('?' + urlencode(context_params))
    return redirect(web_url_for('project_binderhub',
                                pid=node._id) + context_query)
