from flask import request
from modularodm import fields
from modularodm import Q
from requests_oauthlib import OAuth1Session
from requests_oauthlib import OAuth2Session

from framework.mongo import ObjectId
from framework.mongo import StoredObject
from website import settings
from website.util import api_url_for

OAUTH1 = 1
OAUTH2 = 2


class ExternalAccount(StoredObject):
    _id = fields.StringField(default=lambda: str(ObjectId()))

    state = fields.StringField()
    request_token = fields.StringField()
    request_token_secret = fields.StringField()
    access_token = fields.StringField()
    access_token_secret = fields.StringField()
    refresh_token = fields.StringField()

    scopes = fields.StringField(list=True, default=lambda: list())

    # The `name` of the service
    provider = fields.StringField(required=True)

    # The unique, persistent ID on the remote service.
    provider_id = fields.StringField()


def get_service(name):
    """Given a service name, return the provider class"""
    lookup = {
        'zotero': Zotero,
        'orcid': Orcid,
        'mendeley': Mendeley,
    }
    return lookup[name]()


class ExternalProvider(object):
    """

    """

    account = None
    _oauth_version = OAUTH2

    @property
    def auth_url_base(self):
        """The base URL to begin the OAuth dance"""
        raise NotImplementedError

    @property
    def auth_url(self):
        """The URL to begin the OAuth dance.

        Accessing this property will create an ``ExternalAccount`` if one is not
        already attached to the instance, in order to store the state token and
        scope."""

        # create an account if necessary; we need a scope specified
        if self.account is None:
            self.account = ExternalAccount(provider=self.short_name,
                                           scopes=self.default_scopes)

        if self._oauth_version == OAUTH2:
            # build the URL
            session = OAuth2Session(
                self.client_id,
                redirect_uri=api_url_for('oauth_callback',
                                         service_name=self.short_name,
                                         _absolute=True),
                scope=self.account.scopes,
            )

            url, state = session.authorization_url(self.auth_url_base)

            # save state token to the account instance to be available in callback
            self.account.state = state

        elif self._oauth_version == OAUTH1:
            # get a request token
            session = OAuth1Session(
                client_key=self.client_id,
                client_secret=self.client_secret,
            )

            response = session.fetch_request_token(self.request_token_url)

            self.account.request_token = response.get('oauth_token')
            self.account.request_token_secret = response.get('oauth_token_secret')

            url = session.authorization_url(self.auth_url_base)

        self.account.save()

        return url

    @property
    def callback_url(self):
        """The provider URL to exchange the code for a token"""
        raise NotImplementedError()

    @property
    def client_id(self):
        """OAuth Client ID. a/k/a: Application ID"""
        raise NotImplementedError()

    @property
    def client_secret(self):
        """OAuth Client Secret. a/k/a: Application Secret, Application Key"""
        raise NotImplementedError()

    default_scopes = list()

    @property
    def name(self):
        """Human-readable name of the service. e.g.: ORCiD, GitHub"""
        raise NotImplementedError()

    @property
    def short_name(self):
        """Name of the service to be used internally. e.g.: orcid, github"""
        raise NotImplementedError()

    def auth_callback(self, code, state, account=None):
        if self._oauth_version == 1:
            request_token = request.args.get('oauth_token')

            if self.account is None:
                self.account = ExternalAccount.find_one(
                    Q('provider', 'eq', self.short_name) &
                    Q('request_token', 'eq', request_token)
                )

            # TODO: Verify account matches the token provided



            session = OAuth1Session(
                client_key=self.client_id,
                client_secret=self.client_secret,
                resource_owner_key=self.account.request_token,
                resource_owner_secret=self.account.request_token_secret,
                verifier=request.args.get('oauth_verifier')
            )

            response = session.fetch_access_token(self.access_token_url)

            # Clear temp credentials
            self.account.request_token = None
            self.account.request_token_secret = None

        elif self._oauth_version == 2:
            session = OAuth2Session(
                self.client_id,
                redirect_uri=api_url_for('oauth_callback',
                                         service_name=self.short_name,
                                         _absolute=True),
            )

            if self.account is None:
                self.account = ExternalAccount.find_one(
                    Q('provider', 'eq', self.short_name) &
                    Q('state', 'eq', state)
                )

            response = session.fetch_token(
                self.callback_url,
                client_secret=self.client_secret,
                code=code,
            )

            # Clear the state on the account
            self.account.state = None

        self.handle_callback(response)
        self.account.save()

    def handle_callback(self):
        raise NotImplementedError()


class Zotero(ExternalProvider):
    name = 'Zotero'
    short_name = 'zotero'

    client_id = settings.ZOTERO_CLIENT_ID
    client_secret = settings.ZOTERO_CLIENT_SECRET

    _oauth_version = OAUTH1
    auth_url_base = 'https://www.zotero.org/oauth/authorize'
    request_token_url = 'https://www.zotero.org/oauth/request'
    access_token_url = 'https://www.zotero.org/oauth/access'

    def handle_callback(self, data):
        self.account.provider_id = data['userID']
        self.account.access_token = data['oauth_token']
        self.account.access_token_secret = data['oauth_token_secret']


class Orcid(ExternalProvider):
    name = 'ORCiD'
    short_name = 'orcid'

    client_id = settings.ORCID_CLIENT_ID
    client_secret = settings.ORCID_CLIENT_SECRET

    auth_url_base = 'https://orcid.org/oauth/authorize'
    callback_url = 'https://pub.orcid.org/oauth/token'
    default_scopes = ['/authenticate']

    def handle_callback(self, data):
        self.account.access_token = data['access_token']
        self.account.provider_id = data['orcid']


class Github(ExternalProvider):
    name = 'GitHub'
    short_name = 'github'

    client_id = settings.GITHUB_CLIENT_ID
    client_secret = settings.GITHUB_CLIENT_SECRET

    auth_url_base = 'https://github.com/login/oauth/authorize'
    callback_url = 'https://github.com/login/oauth/access_token'

    def handle_callback(self, data):
        self.account.access_token = data['access_token']
        self.account.scopes = data['scope']


class Mendeley(ExternalProvider):
    name = "Mendeley"
    short_name = "mendeley"

    client_id = settings.MENDELEY_CLIENT_ID
    client_secret = settings.MENDELEY_CLIENT_SECRET

    auth_url_base = 'https://api.mendeley.com/oauth/authorize'
    callback_url = 'https://api.mendeley.com/oauth/token'
    default_scopes = ['all']

    def handle_callback(self, data):
        self.account.refresh_token = data['refresh_token']
        self.account.access_token = data['access_token']
        self.account.scopes = data['scope']
        # handle expiration