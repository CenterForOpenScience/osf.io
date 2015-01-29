import abc
import datetime
import logging

from flask import request
from modularodm import fields
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from requests_oauthlib import OAuth1Session
from requests_oauthlib import OAuth2Session

from framework.exceptions import PermissionsError
from framework.mongo import ObjectId
from framework.mongo import StoredObject
from website import settings
from website.oauth.utils import PROVIDER_LOOKUP
from website.util import api_url_for


logger = logging.getLogger(__name__)

OAUTH1 = 1
OAUTH2 = 2


class ExternalAccount(StoredObject):
    _id = fields.StringField(default=lambda: str(ObjectId()))

    temporary = fields.BooleanField(required=True, default=True)
    oauth_key = fields.StringField()
    oauth_secret = fields.StringField()
    refresh_token = fields.StringField()
    expires_at = fields.DateTimeField()

    scopes = fields.StringField(list=True, default=lambda: list())

    # The `name` of the service
    provider = fields.StringField(required=True)

    # The unique, persistent ID on the remote service.
    provider_id = fields.StringField()


class ExternalProviderMeta(abc.ABCMeta):

    def __init__(cls, name, bases, dct):
        super(ExternalProviderMeta, cls).__init__(name, bases, dct)
        if not isinstance(cls.short_name, abc.abstractproperty):
            PROVIDER_LOOKUP[cls.short_name] = cls


class ExternalProvider(object):
    """

    """

    __metaclass__ = ExternalProviderMeta

    account = None
    _oauth_version = OAUTH2

    @abc.abstractproperty
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
            self.account.oauth_key = state

        elif self._oauth_version == OAUTH1:
            # get a request token
            session = OAuth1Session(
                client_key=self.client_id,
                client_secret=self.client_secret,
            )

            response = session.fetch_request_token(self.request_token_url)

            self.account.oauth_key = response.get('oauth_token')
            self.account.oauth_secret = response.get('oauth_token_secret')

            url = session.authorization_url(self.auth_url_base)

        self.account.temporary = True
        self.account.save()

        return url

    @abc.abstractproperty
    def callback_url(self):
        """The provider URL to exchange the code for a token"""
        raise NotImplementedError()

    @abc.abstractproperty
    def client_id(self):
        """OAuth Client ID. a/k/a: Application ID"""
        raise NotImplementedError()

    @abc.abstractproperty
    def client_secret(self):
        """OAuth Client Secret. a/k/a: Application Secret, Application Key"""
        raise NotImplementedError()

    default_scopes = list()

    @abc.abstractproperty
    def name(self):
        """Human-readable name of the service. e.g.: ORCiD, GitHub"""
        raise NotImplementedError()

    @abc.abstractproperty
    def short_name(self):
        """Name of the service to be used internally. e.g.: orcid, github"""
        raise NotImplementedError()

    def auth_callback(self, user):
        # Get the associated ExternalAccount instance for token
        if self._oauth_version == 1:
            request_token = request.args.get('oauth_token')

            self.account = ExternalAccount.find_one(
                Q('provider', 'eq', self.short_name) &
                Q('oauth_key', 'eq', request_token) &
                Q('temporary', 'eq', True)
            )
        elif self._oauth_version == 2:
            state = request.args.get('state')

            self.account = ExternalAccount.find_one(
                Q('provider', 'eq', self.short_name) &
                Q('oauth_key', 'eq', state) &
                Q('temporary', 'eq', True)
            )

        # Make sure the user owns the ExternalAccount
        if self.account not in user.external_accounts:
            raise PermissionsError("User does not match ExternalAccount's owner.")

        if self._oauth_version == 1:

            verifier = request.args.get('oauth_verifier')


            # TODO: Verify account matches the token provided

            session = OAuth1Session(
                client_key=self.client_id,
                client_secret=self.client_secret,
                resource_owner_key=self.account.oauth_key,
                resource_owner_secret=self.account.oauth_secret,
                verifier=verifier
            )

            response = session.fetch_access_token(self.callback_url)

            # TODO: See if the format of the response is in the spec

        elif self._oauth_version == 2:
            code = request.args.get('code')
            session = OAuth2Session(
                self.client_id,
                redirect_uri=api_url_for('oauth_callback',
                                         service_name=self.short_name,
                                         _absolute=True),
            )

            response = session.fetch_token(
                self.callback_url,
                client_secret=self.client_secret,
                code=code,
            )

        self.handle_callback(response)
        self.account.temporary = False
        self.account.save()

    def handle_callback(self, data):
        if self._oauth_version == OAUTH1:
            self.account.oauth_key = data['oauth_token']
            self.account.oauth_secret = data['oauth_token_secret']

        elif self._oauth_version == OAUTH2:
            self.account.refresh_token = data['refresh_token']
            self.account.expires_at = datetime.datetime.fromtimestamp(
                float(data['expires_at'])
            )
            self.account.oauth_key = data['access_token']
            self.account.scopes = data['scope']


class Zotero(ExternalProvider):
    name = 'Zotero'
    short_name = 'zotero'

    client_id = settings.ZOTERO_CLIENT_ID
    client_secret = settings.ZOTERO_CLIENT_SECRET

    _oauth_version = OAUTH1
    auth_url_base = 'https://www.zotero.org/oauth/authorize'
    request_token_url = 'https://www.zotero.org/oauth/request'
    callback_url = 'https://www.zotero.org/oauth/access'

    def handle_callback(self, data):
        self.account.provider_id = data['userID']
        self.account.oauth_key = data['oauth_token']
        self.account.oauth_secret = data['oauth_token_secret']


class Orcid(ExternalProvider):
    name = 'ORCiD'
    short_name = 'orcid'

    client_id = settings.ORCID_CLIENT_ID
    client_secret = settings.ORCID_CLIENT_SECRET

    auth_url_base = 'https://orcid.org/oauth/authorize'
    callback_url = 'https://pub.orcid.org/oauth/token'
    default_scopes = ['/authenticate']

    def handle_callback(self, data):
        self.account.oauth_key = data['access_token']
        self.account.provider_id = data['orcid']


class Github(ExternalProvider):
    name = 'GitHub'
    short_name = 'github'

    client_id = settings.GITHUB_CLIENT_ID
    client_secret = settings.GITHUB_CLIENT_SECRET

    auth_url_base = 'https://github.com/login/oauth/authorize'
    callback_url = 'https://github.com/login/oauth/access_token'

    def handle_callback(self, data):
        self.account.oauth_key = data['access_token']
        self.account.scopes = data['scope']


class Mendeley(ExternalProvider):
    name = "Mendeley"
    short_name = "mendeley"

    client_id = settings.MENDELEY_CLIENT_ID
    client_secret = settings.MENDELEY_CLIENT_SECRET

    auth_url_base = 'https://api.mendeley.com/oauth/authorize'
    callback_url = 'https://api.mendeley.com/oauth/token'
    default_scopes = ['all']


class Linkedin(ExternalProvider):
    name = "LinkedIn"
    short_name = "linkedin"

    client_id = settings.LINKEDIN_CLIENT_ID
    client_secret = settings.LINKEDIN_CLIENT_SECRET

    auth_url_base = 'https://www.linkedin.com/uas/oauth2/authorization'
    callback_url = 'https://www.linkedin.com/uas/oauth2/accessToken'

    def handle_callback(self, data):
        self.account.oauth_key = data['access_token']