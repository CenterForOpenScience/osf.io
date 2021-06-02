# -*- coding: utf-8 -*-
import json
from rest_framework import status as http_status
from flask import request
from flask import redirect
import logging
import requests
from future.moves.urllib.parse import urljoin

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
from .models import BinderHubToken
from . import SHORT_NAME
from . import settings

logger = logging.getLogger(__name__)

def get_client_settings(service_id, auth, node):
    if service_id == 'binderhub':
        client_settings = settings.BINDERHUB_OAUTH_CLIENT
    else:
        tokens = BinderHubToken.objects.filter(user=auth.user, node=node)
        if len(tokens) == 0:
            logger.error('Not logged in to BinderHub')
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        token = tokens[0]
        clients = settings.JUPYTERHUB_OAUTH_CLIENTS
        if token.jupyterhub_url not in clients:
            logger.error('Unexpected JupyterHub: {}'.format(token.jupyterhub_url))
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        client_settings = clients[token.jupyterhub_url]
    return client_settings


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
    # create a dict on the session object if it's not already there
    if session.data.get('oauth_states') is None:
        session.data['oauth_states'] = {}

    client_settings = get_client_settings(service_id, auth, node)

    # build the URL
    oauth = OAuth2Session(
        client_settings['client_id'],
        redirect_uri=api_url_for('binderhub_oauth_callback', _absolute=True),
        scope=client_settings['scope'],
    )

    url, state = oauth.authorization_url(client_settings['authorize_url'])

    # save state token to the session for confirmation in the callback
    session.data['oauth_states'][SHORT_NAME] = {
        'state': state,
        'node_id': node._id,
        'service_id': service_id
    }

    session.save()
    return redirect(url)


@must_be_logged_in
def binderhub_oauth_callback(**kwargs):
    auth = kwargs['auth']
    # make sure the user has temporary credentials for this provider
    try:
        cached_credentials = session.data['oauth_states'][SHORT_NAME]
    except KeyError:
        raise PermissionsError('OAuth flow not recognized.')
    service_id = cached_credentials['service_id']
    node = AbstractNode.objects.get(guids___id=cached_credentials['node_id'])
    client_settings = get_client_settings(service_id, auth, node)

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

        tokens = BinderHubToken.objects.filter(user=auth.user, node=node)
        if len(tokens) > 0:
            token = tokens[0]
        else:
            token = BinderHubToken.objects.create(user=auth.user, node=node)
        if service_id == 'binderhub':
            update_binderhub_data(client_settings, token, response)
        else:
            update_jupyterhub_data(client_settings, token, response)
        token.save()
    except (MissingTokenError, RequestsHTTPError):
        raise HTTPError(http_status.HTTP_503_SERVICE_UNAVAILABLE)
    return redirect(web_url_for('project_binderhub',
                                pid=node._id))
