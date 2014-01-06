"""
Get access to GitHub using OAuth 2.0.
"""

import os
from requests_oauthlib import OAuth2Session

from website import settings
from . import settings as github_settings

OAUTH_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
OAUTH_ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'


def oauth_start_url(user, node=None):
    """Get authorization URL for OAuth.

    :param User user: OSF user
    :param Node node: OSF node
    :return tuple: Tuple of authorization URL and OAuth state

    """
    uri_parts = [
        settings.DOMAIN, 'api', 'v1', 'addons', 'github',
        'callback', user._id,
    ]
    if node:
        uri_parts.append(node._id)
    redirect_uri = os.path.join(*uri_parts)

    session = OAuth2Session(
        github_settings.CLIENT_ID,
        redirect_uri=redirect_uri,
        scope=github_settings.SCOPE,
    )

    return session.authorization_url(OAUTH_AUTHORIZE_URL)


def oauth_get_token(code):
    """Get OAuth access token.

    :param str code: Authorization code from provider
    :return str: OAuth access token

    """
    session = OAuth2Session(
        github_settings.CLIENT_ID,
    )
    return session.fetch_token(
        OAUTH_ACCESS_TOKEN_URL,
        client_secret=github_settings.CLIENT_SECRET,
        code=code,
    )
