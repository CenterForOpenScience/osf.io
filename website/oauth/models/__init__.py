# -*- coding: utf-8 -*-

import abc
import logging
import datetime
import httplib as http

import pymongo
from flask import request
from modularodm import Q
from modularodm import fields
from modularodm.storage.base import KeyExistsException
from requests_oauthlib import OAuth1Session
from requests_oauthlib import OAuth2Session

from framework.exceptions import HTTPError
from framework.exceptions import PermissionsError
from framework.mongo import ObjectId
from framework.mongo import StoredObject
from framework.sessions import get_session

from website.util import web_url_for
from oauthlib.oauth2.rfc6749.errors import MissingTokenError
from website.oauth.utils import PROVIDER_LOOKUP


logger = logging.getLogger(__name__)

OAUTH1 = 1
OAUTH2 = 2


class ExternalAccount(StoredObject):
    __indices__ = [
        {
            'key_or_list': [
                ('provider', pymongo.ASCENDING),
                ('provider_id', pymongo.ASCENDING),
            ],
            'unique': True,
        }
    ]
    _id = fields.StringField(default=lambda: str(ObjectId()), primary=True)

    oauth_key = fields.StringField()
    oauth_secret = fields.StringField()
    refresh_token = fields.StringField()
    expires_at = fields.DateTimeField()

    scopes = fields.StringField(list=True, default=lambda: list())

    # The `name` of the service
    provider = fields.StringField(required=True)

    # The unique, persistent ID on the remote service.
    provider_id = fields.StringField()

    display_name = fields.StringField()
    profile_url = fields.StringField()

    def __repr__(self):
        return '<ExternalAccount: {}/{}>'.format(self.provider,
                                                 self.provider_id)


class ExternalProviderMeta(abc.ABCMeta):

    def __init__(cls, name, bases, dct):
        super(ExternalProviderMeta, cls).__init__(name, bases, dct)
        if not isinstance(cls.short_name, abc.abstractproperty):
            PROVIDER_LOOKUP[cls.short_name] = cls


class ExternalProvider(object):
    """

    """

    __metaclass__ = ExternalProviderMeta

    _oauth_version = OAUTH2

    def __init__(self):
        super(ExternalProvider, self).__init__()

        self.account = None

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )

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

        session = get_session()

        # create a dict on the session object if it's not already there
        if session.data.get("oauth_states") is None:
            session.data['oauth_states'] = {}

        if self._oauth_version == OAUTH2:
            # build the URL
            oauth = OAuth2Session(
                self.client_id,
                redirect_uri=web_url_for('oauth_callback',
                                         service_name=self.short_name,
                                         _absolute=True),
                scope=self.default_scopes,
            )

            url, state = oauth.authorization_url(self.auth_url_base)

            # save state token to the account instance to be available in callback
            session.data['oauth_states'][self.short_name] = {'state': state}

        elif self._oauth_version == OAUTH1:
            # get a request token
            oauth = OAuth1Session(
                client_key=self.client_id,
                client_secret=self.client_secret,
            )

            response = oauth.fetch_request_token(self.request_token_url)

            session.data['oauth_states'][self.short_name] = {
                'token': response.get('oauth_token'),
                'secret': response.get('oauth_token_secret'),
            }

            url = oauth.authorization_url(self.auth_url_base)

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
        session = get_session()

        try:
            cached_credentials = session.data['oauth_states'][self.short_name]
        except KeyError:
            raise PermissionsError("OAuth flow not recognized.")

        if self._oauth_version == OAUTH1:
            request_token = request.args.get('oauth_token')

            if cached_credentials.get('token') != request_token:
                raise PermissionsError("Request token does not match")

            response = OAuth1Session(
                client_key=self.client_id,
                client_secret=self.client_secret,
                resource_owner_key=cached_credentials.get('token'),
                resource_owner_secret=cached_credentials.get('secret'),
                verifier=request.args.get('oauth_verifier'),
            ).fetch_access_token(self.callback_url)

        elif self._oauth_version == OAUTH2:
            state = request.args.get('state')

            if cached_credentials.get('state') != state:
                raise PermissionsError("Request token does not match")

            try:
                response = OAuth2Session(
                    self.client_id,
                    redirect_uri=web_url_for(
                        'oauth_callback',
                        service_name=self.short_name,
                        _absolute=True
                    ),
                ).fetch_token(
                    self.callback_url,
                    client_secret=self.client_secret,
                    code=request.args.get('code'),
                )
            except MissingTokenError:
                raise HTTPError(http.SERVICE_UNAVAILABLE)

        info = self._default_handle_callback(response)
        info.update(self.handle_callback(response))

        try:
            self.account = ExternalAccount(
                provider=self.short_name,
                provider_id=info['provider_id'],
            )
            self.account.save()
        except KeyExistsException:
            self.account = ExternalAccount.find_one(
                Q('provider', 'eq', self.short_name) &
                Q('provider_id', 'eq', info['provider_id'])
            )
            assert self.account is not None

        # required
        self.account.oauth_key = info['key']

        # only for OAuth1
        self.account.oauth_secret = info.get('secret')

        # only for OAuth2
        self.account.expires_at = info.get('expires_at')
        self.account.refresh_token = info.get('refresh_token')

        # additional information
        self.account.display_name = info.get('display_name')
        self.account.profile_url = info.get('profile_url')

        self.account.save()

        if self.account not in user.external_accounts:
            user.external_accounts.append(self.account)
            user.save()

    def _default_handle_callback(self, data):
        if self._oauth_version == OAUTH1:
            key = data.get('oauth_token')
            secret = data.get('oauth_token_secret')

            values = {}

            if key:
                values['key'] = key
            if secret:
                values['secret'] = secret

            return values

        elif self._oauth_version == OAUTH2:
            key = data.get('access_token')
            refresh_token = data.get('refresh_token')
            expires_at = data.get('expires_at')
            scopes = data.get('scope')

            values = {}

            if key:
                values['key'] = key
            if scopes:
                values['scope'] = scopes
            if refresh_token:
                values['refresh_token'] = refresh_token
            if expires_at:
                values['expires_at'] = datetime.datetime.fromtimestamp(
                    float(expires_at)
                )

            return values

    def handle_callback(self, response):
        return {}
