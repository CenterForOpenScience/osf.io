import httplib as http
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


class WEKOProvider(ExternalProvider):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'WEKO'
    short_name = 'weko'
    serializer = WEKOSerializer

    client_id = None
    client_secret = None
    auth_url_base = None
    callback_url = None

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
        rid = self.account.provider_id.split(':')[0]
        if rid == REPOID_BASIC_AUTH:
            return None
        return rid

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
            return weko_settings.REPOSITORIES[repoid]['host']
        else:
            return self.account.profile_url

    @property
    def password(self):
        if self.repoid is not None:
            return None
        else:
            return self.account.oauth_key

    @property
    def token(self):
        if self.repoid is not None:
            return self.account.oauth_key
        else:
            return None

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

        repo_settings = weko_settings.REPOSITORIES[repoid]

        assert self._oauth_version == OAUTH2
        # build the URL
        oauth = OAuth2Session(
            repo_settings['client_id'],
            redirect_uri=web_url_for('weko_oauth_callback',
                                     repoid=repoid,
                                     _absolute=True),
            scope=self.default_scopes,
        )

        url, state = oauth.authorization_url(repo_settings['authorize_url'])

        # save state token to the session for confirmation in the callback
        session.data['oauth_states'][self.short_name] = {'state': state}

        session.save()
        return url

    def repo_auth_callback(self, user, repoid, **kwargs):
        """Exchange temporary credentials for permanent credentials

        This is called in the view that handles the user once they are returned
        to the OSF after authenticating on the external service.
        """

        if 'error' in request.args:
            return False

        repo_settings = weko_settings.REPOSITORIES[repoid]

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

        try:
            callback_url = web_url_for('weko_oauth_callback', repoid=repoid,
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
            raise HTTPError(http.SERVICE_UNAVAILABLE)
        # pre-set as many values as possible for the ``ExternalAccount``
        info = self._default_handle_callback(response)
        # call the hook for subclasses to parse values from the response
        info.update(self.handle_callback(repoid, response))

        return self._set_external_account(user, info)

    def handle_callback(self, repoid, response):
        """View called when the OAuth flow is completed.
        """
        from addons.weko.client import connect_or_error

        repo_settings = weko_settings.REPOSITORIES[repoid]
        connection = connect_or_error(repo_settings['host'],
                                      token=response.get('access_token'))
        login_user = connection.get_login_user('unknown')
        return {
            'provider_id': '{}:{}'.format(repoid, login_user),
            'display_name': login_user + '@' + repoid
        }
