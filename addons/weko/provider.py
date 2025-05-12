import logging
from future.moves.urllib.parse import urljoin

from rest_framework import status as http_status
from flask import request
from framework.exceptions import HTTPError
from oauthlib.oauth2.rfc6749.errors import MissingTokenError
from requests.exceptions import HTTPError as RequestsHTTPError
from osf.models import ExternalAccount

from osf.models.external import ExternalProvider
from framework.exceptions import PermissionsError
from framework.sessions import session
from website.util import web_url_for
from requests_oauthlib import OAuth2Session

from addons.weko.serializer import WEKOSerializer
from addons.weko import settings as weko_settings


OAUTH2 = 2
REPOID_BASIC_AUTH = '_basic'

logger = logging.getLogger(__name__)


def _get_repoid(account):
    rid = account.provider_id.split(':')[0]
    if rid == REPOID_BASIC_AUTH:
        return None
    return rid

def _get_repodomain_from_repoid(repoid):
    pos = repoid.rindex('.')
    if pos == -1:
        raise ValueError('Invalid repoid: ' + repoid)
    return repoid[:pos]

def find_repository(repoid):
    logger.debug(f'find_repository by id: {repoid}')
    if repoid in weko_settings.REPOSITORIES:
        return weko_settings.REPOSITORIES[repoid]
    account = ExternalAccount.objects.get(provider_id=repoid)
    url = account.display_name
    if '#' in account.display_name:
        url = account.display_name[:account.display_name.index('#')]
    return {
        'host': urljoin(url, 'sword/'),
        'client_id': account.oauth_key,
        'client_secret': account.oauth_secret,
        'authorize_url': urljoin(url, 'oauth/authorize'),
        'access_token_url': urljoin(url, 'oauth/token'),
    }

class WEKOProvider(ExternalProvider):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'WEKO'
    short_name = 'weko'
    serializer = WEKOSerializer

    auth_url_base = None
    callback_url = None
    default_scopes = ['deposit:actions deposit:write index:create user:activity user:email']
    refresh_time = weko_settings.REFRESH_TIME

    def __init__(self, account=None, host=None, username=None, password=None):
        super(WEKOProvider, self).__init__(account=account)
        if account:
            self.account = account
        elif not account and host and password and username:
            self.account = ExternalAccount(
                display_name=username,
                oauth_key=password,
                oauth_secret=host,
                provider_id='{}:{}:{}'.format(REPOID_BASIC_AUTH, host, username),
                profile_url=host,
                provider=self.short_name,
                provider_name=self.name
            )
        else:
            self.account = None

    @property
    def repoid(self):
        return _get_repoid(self.account)

    @property
    def userid(self):
        if self.repoid is None:
            return self.account.display_name
        else:
            provider_id = self.account.provider_id
            return provider_id[provider_id.index(':') + 1:]

    @property
    def sword_url(self):
        repoid = self.repoid
        if repoid is not None:
            return find_repository(_get_repoid(self.account))['host']
        else:
            return self.account.profile_url

    @property
    def password(self):
        if self.repoid is not None:
            return None
        else:
            return self.account.oauth_key

    @property
    def auto_refresh_url(self):
        repoid = self.repoid
        if repoid is None:
            return None
        repo_settings = find_repository(_get_repoid(self.account))
        return repo_settings['access_token_url']

    @property
    def client_id(self):
        repoid = self.repoid
        if repoid is None:
            return None
        repo_settings = find_repository(_get_repoid(self.account))
        return repo_settings['client_id']

    @property
    def client_secret(self):
        repoid = self.repoid
        if repoid is None:
            return None
        repo_settings = find_repository(_get_repoid(self.account))
        return repo_settings['client_secret']

    def fetch_access_token(self, force_refresh=False):
        refreshed = self.refresh_oauth_key(force=force_refresh)
        logger.debug('auto_refresh_url: ' + self.auto_refresh_url)
        logger.debug('refresh_oauth_key returns {}, {}'.format(refreshed, self.account.oauth_key))
        return self.account.oauth_key

    def get_repo_auth_url(self, repoid):
        """The URL to begin the OAuth dance.

        This property method has side effects - it at least adds temporary
        information to the session so that callbacks can be associated with
        the correct user.  For OAuth1, it calls the provider to obtain
        temporary credentials to start the flow.
        """

        # create a dict on the session object if it's not already there
        if session.data.get('oauth_states') is None:
            session.data['oauth_states'] = {}

        repo_settings = find_repository(repoid)
        repodomain = _get_repodomain_from_repoid(repoid)

        assert self._oauth_version == OAUTH2
        # build the URL
        oauth = OAuth2Session(
            repo_settings['client_id'],
            redirect_uri=web_url_for('weko_oauth_callback',
                                     repodomain=repodomain,
                                     _absolute=True),
            scope=self.default_scopes,
        )

        url, state = oauth.authorization_url(repo_settings['authorize_url'])

        # save state token to the session for confirmation in the callback
        session.data['oauth_states'][self.short_name] = {
            'state': state,
            'repoid': repoid,
        }

        session.save()
        return url

    def repo_auth_callback(self, user, repodomain, **kwargs):
        """Exchange temporary credentials for permanent credentials

        This is called in the view that handles the user once they are returned
        to the GakuNin RDM after authenticating on the external service.
        """

        if 'error' in request.args:
            return False

        # make sure the user has temporary credentials for this provider
        try:
            cached_credentials = session.data['oauth_states'][self.short_name]
        except KeyError:
            raise PermissionsError('OAuth flow not recognized.')

        assert self._oauth_version == OAUTH2
        state = request.args.get('state')

        # make sure this is the same user that started the flow
        if cached_credentials.get('state') != state:
            raise PermissionsError('Request token does not match')

        # repoid from session
        repoid = cached_credentials['repoid']
        repo_settings = find_repository(repoid)
        try:
            callback_url = web_url_for('weko_oauth_callback', repodomain=repodomain,
                                       _absolute=True)
            response = OAuth2Session(
                repo_settings['client_id'],
                redirect_uri=callback_url,
            ).fetch_token(
                repo_settings['access_token_url'],
                client_secret=repo_settings['client_secret'],
                code=request.args.get('code'),
            )
        except (MissingTokenError, RequestsHTTPError):
            # Error messages are not output to the logger according to
            # the policy of ExternalProvider.auth_callback in osf.models.external
            raise HTTPError(http_status.HTTP_503_SERVICE_UNAVAILABLE)
        # pre-set as many values as possible for the ``ExternalAccount``
        info = self._default_handle_callback(response)
        # call the hook for subclasses to parse values from the response
        info.update(self.handle_callback(repoid, response))

        return self._set_external_account(user, info)

    def handle_callback(self, repoid, response):
        """View called when the OAuth flow is completed.
        """
        from addons.weko.client import Client

        repo_settings = find_repository(repoid)
        c = Client(repo_settings['host'], token=response.get('access_token'))
        login_user = c.get_login_user('unknown@' + repoid)
        return {
            'provider_id': '{}:{}'.format(repoid, login_user),
            'display_name': login_user
        }
