import hashlib
import json

import requests

from website import settings

def provision_node(node):
    response = requests.post(
        settings.PIWIK_HOST,
        data={
            'module': 'API',
            'token_auth': settings.PIWIK_ADMIN_TOKEN,
            'format': 'json',
            'method': 'SitesManager.addSite',
            'siteName': 'Node: ' + node._id,
            'urls': [
                settings.CANONICAL_DOMAIN + node.url,
                settings.SHORT_DOMAIN + node.url,
            ],
        }
    )

    try:
        piwik_site_id = json.loads(response.content)['value']
    except (ValueError, KeyError):
        raise Exception('Piwik site creation failed')

    piwik_user_id = 'node_' + node._id
    piwik_password = hashlib.sha256(
        node._id + settings.SECRET_KEY
    ).hexdigest()[:6]
    piwik_password_hash = hashlib.md5(piwik_password).hexdigest()

    response = requests.post(
        settings.PIWIK_HOST,
        data={
            'module': 'API',
            'token_auth': settings.PIWIK_ADMIN_TOKEN,
            'format': 'json',
            'method': 'UsersManager.addUser',
            'userLogin': piwik_user_id,
            'password': piwik_password,
            'email': node._id + '@osf.io',
            'alias': node._id,
        }
    )

    try:
        assert json.loads(response.content).get('result') == 'success'
    except AssertionError:
        raise Exception('Piwik user creation failed')

    response = requests.post(
        settings.PIWIK_HOST,
        data={
            'module': 'API',
            'token_auth': settings.PIWIK_ADMIN_TOKEN,
            'format': 'json',
            'method': 'UsersManager.setUserAccess',
            'userLogin': piwik_user_id,
            'access': 'view',
            'idSites': [piwik_site_id, ]
        }
    )

    try:
        assert json.loads(response.content).get('result') == 'success'
    except AssertionError:
        raise Exception('Piwik user privilege grant failed')


    response = requests.post(
        settings.PIWIK_HOST,
        data={
            'module': 'API',
            'format': 'json',
            'method': 'UsersManager.getTokenAuth',
            'userLogin': piwik_user_id,
            'md5Password': piwik_password_hash
        }
    )

    try:
        piwik_user_token = json.loads(response.content)['value']
    except (ValueError, KeyError):
        raise Exception('Piwik token request failed')

    node.piwik_credentials = {
        'site_id': piwik_site_id,
        'auth_token': piwik_user_token,
        'password_hash': piwik_password_hash,
    }

    node.save()

    return True