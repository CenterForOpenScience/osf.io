import abc
import datetime as dt
import functools
from rest_framework import status as http_status
import logging

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from flask import request
from oauthlib.oauth2 import (AccessDeniedError, InvalidGrantError,
    TokenExpiredError, MissingTokenError)
from requests.exceptions import HTTPError as RequestsHTTPError
from requests_oauthlib import OAuth1Session, OAuth2Session

from framework.exceptions import HTTPError, PermissionsError
from framework.sessions import session
from osf.models import base
from osf.utils.fields import EncryptedTextField, NonNaiveDateTimeField
from website.oauth.utils import PROVIDER_LOOKUP
from website.security import random_string
from website.settings import ADDONS_OAUTH_NO_REDIRECT
from website.util import web_url_for
from future.utils import with_metaclass

logger = logging.getLogger(__name__)

OAUTH1 = 1
OAUTH2 = 2

generate_client_secret = functools.partial(random_string, length=40)

class ExternalAccount(base.ObjectIDMixin, base.BaseModel):
    """An account on an external service.

    Note that this object is not and should not be aware of what other objects
    are associated with it. This is by design, and this object should be kept as
    thin as possible, containing only those fields that must be stored in the
    database.

    The ``provider`` field is a de facto foreign key to an ``ExternalProvider``
    object, as providers are not stored in the database.
    """

    # The OAuth credentials. One or both of these fields should be populated.
    # For OAuth1, this is usually the "oauth_token"
    # For OAuth2, this is usually the "access_token"
    oauth_key = EncryptedTextField(blank=True, null=True)

    # For OAuth1, this is usually the "oauth_token_secret"
    # For OAuth2, this is not used
    oauth_secret = EncryptedTextField(blank=True, null=True)

    # Used for OAuth2 only
    refresh_token = EncryptedTextField(blank=True, null=True)
    date_last_refreshed = NonNaiveDateTimeField(blank=True, null=True)
    expires_at = NonNaiveDateTimeField(blank=True, null=True)
    scopes = ArrayField(models.CharField(max_length=128), default=list, blank=True)

    # The `name` of the service
    # This lets us query for only accounts on a particular provider
    # TODO We should make provider an actual FK someday.
    provider = models.CharField(max_length=50, blank=False, null=False)
    # The proper 'name' of the service
    # Needed for account serialization
    provider_name = models.CharField(max_length=255, blank=False, null=False)

    # The unique, persistent ID on the remote service.
    provider_id = models.CharField(max_length=255, blank=False, null=False)

    # The user's name on the external service
    display_name = EncryptedTextField(blank=True, null=True)
    # A link to the user's profile on the external service
    profile_url = EncryptedTextField(blank=True, null=True)

    def __repr__(self):
        return '<ExternalAccount: {}/{}>'.format(self.provider,
                                                 self.provider_id)

    def _natural_key(self):
        if self.pk:
            return self.pk
        return hash(str(self.provider_id) + str(self.provider))

    class Meta:
        unique_together = [
            ('provider', 'provider_id',)
        ]


class ExternalProviderMeta(abc.ABCMeta):
    """Keeps track of subclasses of the ``ExternalProvider`` object"""

    def __init__(cls, name, bases, dct):
        super(ExternalProviderMeta, cls).__init__(name, bases, dct)
        if not isinstance(cls.short_name, abc.abstractproperty):
            PROVIDER_LOOKUP[cls.short_name] = cls


class ExternalProvider(with_metaclass(ExternalProviderMeta)):
    """A connection to an external service (ex: GitHub).

    This object contains no credentials, and is not saved in the database.
    It provides an unauthenticated session with the provider, unless ``account``
    has been set - in which case, it provides a connection authenticated as the
    ``ExternalAccount`` instance.

    Conceptually, this can be thought of as an extension of ``ExternalAccount``.
    It's a separate object because this must be subclassed for each provider,
    and ``ExternalAccount`` instances are stored within a single collection.
    """

    # Default to OAuth v2.0.
    _oauth_version = OAUTH2

    # Providers that have expiring tokens must override these
    auto_refresh_url = None
    refresh_time = 0  # When to refresh the oauth_key (seconds)
    expiry_time = 0  # If/When the refresh token expires (seconds). 0 indicates a non-expiring refresh token

    def __init__(self, account=None):
        super(ExternalProvider, self).__init__()

        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )

    @abc.abstractproperty
    def auth_url_base(self):
        """The base URL to begin the OAuth dance"""
        pass

    @property
    def auth_url(self):
        """The URL to begin the OAuth dance.

        This property method has side effects - it at least adds temporary
        information to the session so that callbacks can be associated with
        the correct user.  For OAuth1, it calls the provider to obtain
        temporary credentials to start the flow.
        """

        # create a dict on the session object if it's not already there
        if session.data.get('oauth_states') is None:
            session.data['oauth_states'] = {}

        if self._oauth_version == OAUTH2:
            # Quirk: Some time between 2019/05/31 and 2019/06/04, Bitbucket's OAuth2 API no longer
            #        expects the query param `redirect_uri` in the `oauth2/authorize` endpoint.  In
            #        addition, it relies on the "Callback URL" of the "OAuth Consumer" to redirect
            #        the auth flow after successful authorization.  `ADDONS_OAUTH_NO_REDIRECT` is a
            #        list containing addons that do not use `redirect_uri` in OAuth2 requests.
            if self.short_name in ADDONS_OAUTH_NO_REDIRECT:
                redirect_uri = None
            else:
                redirect_uri = web_url_for(
                    'oauth_callback',
                    service_name=self.short_name,
                    _absolute=True
                )
            # build the URL
            oauth = OAuth2Session(
                self.client_id,
                redirect_uri=redirect_uri,
                scope=self.default_scopes,
            )

            url, state = oauth.authorization_url(self.auth_url_base)

            # save state token to the session for confirmation in the callback
            session.data['oauth_states'][self.short_name] = {'state': state}

        elif self._oauth_version == OAUTH1:
            # get a request token
            oauth = OAuth1Session(
                client_key=self.client_id,
                client_secret=self.client_secret,
            )

            # request temporary credentials from the provider
            response = oauth.fetch_request_token(self.request_token_url)

            # store them in the session for use in the callback
            session.data['oauth_states'][self.short_name] = {
                'token': response.get('oauth_token'),
                'secret': response.get('oauth_token_secret'),
            }

            url = oauth.authorization_url(self.auth_url_base)

        session.save()
        return url

    @abc.abstractproperty
    def callback_url(self):
        """The provider URL to exchange the code for a token"""
        pass

    @abc.abstractproperty
    def client_id(self):
        """OAuth Client ID. a/k/a: Application ID"""
        pass

    @abc.abstractproperty
    def client_secret(self):
        """OAuth Client Secret. a/k/a: Application Secret, Application Key"""
        pass

    default_scopes = list()

    @abc.abstractproperty
    def name(self):
        """Human-readable name of the service. e.g.: ORCiD, GitHub"""
        pass

    @abc.abstractproperty
    def short_name(self):
        """Name of the service to be used internally. e.g.: orcid, github"""
        pass

    def auth_callback(self, user, **kwargs):
        """Exchange temporary credentials for permanent credentials

        This is called in the view that handles the user once they are returned
        to the OSF after authenticating on the external service.
        """

        if 'error' in request.args:
            return False

        # make sure the user has temporary credentials for this provider
        try:
            cached_credentials = session.data['oauth_states'][self.short_name]
        except KeyError:
            raise PermissionsError('OAuth flow not recognized.')

        if self._oauth_version == OAUTH1:
            request_token = request.args.get('oauth_token')

            # make sure this is the same user that started the flow
            if cached_credentials.get('token') != request_token:
                raise PermissionsError('Request token does not match')

            response = OAuth1Session(
                client_key=self.client_id,
                client_secret=self.client_secret,
                resource_owner_key=cached_credentials.get('token'),
                resource_owner_secret=cached_credentials.get('secret'),
                verifier=request.args.get('oauth_verifier'),
            ).fetch_access_token(self.callback_url)

        elif self._oauth_version == OAUTH2:
            state = request.args.get('state')

            # make sure this is the same user that started the flow
            if cached_credentials.get('state') != state:
                raise PermissionsError('Request token does not match')

            try:
                # Quirk: Similarly to the `oauth2/authorize` endpoint, the `oauth2/access_token`
                #        endpoint of Bitbucket would fail if a not-none or non-empty `redirect_uri`
                #        were provided in the body of the POST request.
                if self.short_name in ADDONS_OAUTH_NO_REDIRECT:
                    redirect_uri = None
                else:
                    redirect_uri = web_url_for(
                        'oauth_callback',
                        service_name=self.short_name,
                        _absolute=True
                    )
                response = OAuth2Session(
                    self.client_id,
                    redirect_uri=redirect_uri,
                ).fetch_token(
                    self.callback_url,
                    client_secret=self.client_secret,
                    code=request.args.get('code'),
                )
            except (MissingTokenError, RequestsHTTPError):
                raise HTTPError(http_status.HTTP_503_SERVICE_UNAVAILABLE)
        # pre-set as many values as possible for the ``ExternalAccount``
        info = self._default_handle_callback(response)
        # call the hook for subclasses to parse values from the response
        info.update(self.handle_callback(response))

        return self._set_external_account(user, info)

    def _set_external_account(self, user, info):

        self.account, created = ExternalAccount.objects.get_or_create(
            provider=self.short_name,
            provider_id=info['provider_id'],
        )

        # ensure that provider_name is correct
        self.account.provider_name = self.name
        # required
        self.account.oauth_key = info['key']

        # only for OAuth1
        self.account.oauth_secret = info.get('secret')

        # only for OAuth2
        self.account.expires_at = info.get('expires_at')
        self.account.refresh_token = info.get('refresh_token')
        self.account.date_last_refreshed = timezone.now()

        # additional information
        self.account.display_name = info.get('display_name')
        self.account.profile_url = info.get('profile_url')

        self.account.save()

        # add it to the user's list of ``ExternalAccounts``
        if not user.external_accounts.filter(id=self.account.id).exists():
            user.external_accounts.add(self.account)
            user.save()

        if self.short_name in session.data.get('oauth_states', {}):
            del session.data['oauth_states'][self.short_name]
            session.save()

        return True

    def _default_handle_callback(self, data):
        """Parse as much out of the key exchange's response as possible.

        This should not be over-ridden in subclasses.
        """
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
                values['expires_at'] = dt.datetime.fromtimestamp(
                    float(expires_at)
                )

            return values

    @abc.abstractmethod
    def handle_callback(self, response):
        """Hook for allowing subclasses to parse information from the callback.

        Subclasses should implement this method to provide `provider_id`
        and `profile_url`.

        Values provided by ``self._default_handle_callback`` can be over-ridden
        here as well, in the unexpected case that they are parsed incorrectly
        by default.

        :param response: The JSON returned by the provider during the exchange
        :return dict:
        """
        pass

    def refresh_oauth_key(self, force=False, extra=None, resp_auth_token_key='access_token',
                          resp_refresh_token_key='refresh_token', resp_expiry_fn=None):
        """Handles the refreshing of an oauth_key for account associated with this provider.
           Not all addons need to use this, as some do not have oauth_keys that expire.

        Subclasses must define the following for this functionality:
        `auto_refresh_url` - URL to use when refreshing tokens. Must use HTTPS
        `refresh_time` - Time (in seconds) that the oauth_key should be refreshed after.
                            Typically half the duration of validity. Cannot be 0.

        Providers may have different keywords in their response bodies, kwargs
        `resp_*_key` allow subclasses to override these if necessary.

        kwarg `resp_expiry_fn` allows subclasses to specify a function that will return the
        datetime-formatted oauth_key expiry key, given a successful refresh response from
        `auto_refresh_url`. A default using 'expires_at' as a key is provided.
        """
        extra = extra or {}
        # Ensure this is an authenticated Provider that uses token refreshing
        if not (self.account and self.auto_refresh_url):
            return False

        # Ensure this Provider is for a valid addon
        if not (self.client_id and self.client_secret):
            return False

        # Ensure a refresh is needed
        if not (force or self._needs_refresh()):
            return False

        if self.has_expired_credentials and not force:
            return False

        resp_expiry_fn = resp_expiry_fn or (
            lambda x: timezone.now() + timezone.timedelta(seconds=float(x['expires_in']))
        )

        client = OAuth2Session(
            self.client_id,
            token={
                'access_token': self.account.oauth_key,
                'refresh_token': self.account.refresh_token,
                'token_type': 'Bearer',
                'expires_in': '-30',
            }
        )

        extra.update({
            'client_id': self.client_id,
            'client_secret': self.client_secret
        })

        try:
            token = client.refresh_token(
                self.auto_refresh_url,
                **extra
            )
        except (AccessDeniedError, InvalidGrantError, TokenExpiredError):
            if not force:
                return False
            else:
                raise

        self.account.oauth_key = token[resp_auth_token_key]
        self.account.refresh_token = token[resp_refresh_token_key]
        self.account.expires_at = resp_expiry_fn(token)
        self.account.date_last_refreshed = timezone.now()
        self.account.save()
        return True

    def _needs_refresh(self):
        """Determines whether or not an associated ExternalAccount needs
        a oauth_key.

        return bool: True if needs_refresh
        """
        if self.refresh_time and self.account.expires_at:
            return (self.account.expires_at - timezone.now()).total_seconds() < self.refresh_time
        return False

    @property
    def has_expired_credentials(self):
        """Determines whether or not an associated ExternalAccount has
        expired credentials that can no longer be renewed

        return bool: True if cannot be refreshed
        """
        if self.expiry_time and self.account.expires_at:
            return (timezone.now() - self.account.expires_at).total_seconds() > self.expiry_time
        return False

class BasicAuthProviderMixin(object):
    """
        Providers utilizing BasicAuth can utilize this class to implement the
        storage providers framework by subclassing this mixin. This provides
        a translation between the oauth parameters and the BasicAuth parameters.

        The password here is kept decrypted by default.
    """

    def __init__(self, account=None, host=None, username=None, password=None):
        super(BasicAuthProviderMixin, self).__init__()
        if account:
            self.account = account
        elif not account and host and password and username:
            self.account = ExternalAccount(
                display_name=username,
                oauth_key=password,
                oauth_secret=host,
                provider_id='{}:{}'.format(host, username),
                profile_url=host,
                provider=self.short_name,
                provider_name=self.name
            )
        else:
            self.account = None

    @property
    def host(self):
        return self.account.profile_url

    @property
    def username(self):
        return self.account.display_name

    @property
    def password(self):
        return self.account.oauth_key
