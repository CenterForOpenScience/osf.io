"""

"""

import os
from oauthlib.common import generate_token
from requests_oauthlib import OAuth2Session

from website import settings
from . import settings as github_settings

OAUTH_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
OAUTH_ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'


def oauth_start_url(node, state_suffix):
    """Get authorization URL for OAuth.

    :param Node node: OSF Node
    :param str state_suffix: Optional string to be appended to state
    :return tuple: Tuple of authorization URL and OAuth state

    """
    redirect_uri = os.path.join(
        settings.DOMAIN, 'api', 'v1', 'addons', 'github',
        'callback', node._id,
    )
    state_generator=(
        lambda: generate_token() + state_suffix
        if state_suffix
        else None
    )

    session = OAuth2Session(
        github_settings.CLIENT_ID,
        redirect_uri=redirect_uri,
        scope=github_settings.SCOPE,
        state=state_generator,
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
