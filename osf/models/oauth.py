import uuid

from website.util import api_v2_url

from django.db import models
from osf.models import base
from website.security import random_string

from framework.auth import cas

from website import settings
from urlparse import urljoin


def generate_client_secret():
    return random_string(length=40)


class ApiOAuth2Scope(base.ObjectIDMixin, base.BaseModel):
    """
    Store information about recognized OAuth2 scopes. Only scopes registered under this database model can
        be requested by third parties.
    """
    name = models.CharField(max_length=50, unique=True, db_index=True, null=False, blank=False)
    description = models.CharField(max_length=255, null=False, blank=False)
    is_active = models.BooleanField(default=True, db_index=True)  # TODO: Add mechanism to deactivate a scope?
    is_public = models.BooleanField(default=True, db_index=True)

    def absolute_url(self):
        return urljoin(settings.API_DOMAIN, '/v2/scopes/{}/'.format(self.name))


def generate_client_id():
    return uuid.uuid4().hex


class ApiOAuth2Application(base.ObjectIDMixin, base.BaseModel):
    """Registration and key for user-created OAuth API applications

    This collection is also used by CAS to create the master list of available applications.
    Any changes made to field names in this model must be echoed in the CAS implementation.
    """

    # Client ID and secret. Use separate ID field so ID format doesn't
    # have to be restricted to database internals.
    # Not *guaranteed* unique, but very unlikely
    client_id = models.CharField(default=generate_client_id,
                                 unique=True,
                                 max_length=50,
                                 db_index=True)

    client_secret = models.CharField(default=generate_client_secret, max_length=40)

    is_active = models.BooleanField(default=True,  # Set to False if application is deactivated
                                    db_index=True)

    owner = models.ForeignKey('OSFUser', null=True, blank=True, on_delete=models.SET_NULL)

    # User-specified application descriptors
    name = models.CharField(db_index=True, blank=False, null=False, max_length=200)
    description = models.CharField(blank=True, null=True, max_length=1000)

    home_url = models.URLField(blank=False, null=False)
    callback_url = models.URLField(blank=False, null=False)

    def deactivate(self, save=False):
        """
        Deactivate an ApiOAuth2Application

        Does not delete the database record, but revokes all tokens and sets a
        flag that hides this instance from API
        """
        client = cas.get_client()
        # Will raise a CasHttpError if deletion fails, which will also stop setting of active=False.
        resp = client.revoke_application_tokens(self.client_id, self.client_secret)  # noqa

        self.is_active = False

        if save:
            self.save()
        return True

    def reset_secret(self, save=False):
        """
        Reset the secret of an ApiOAuth2Application
        Revokes all tokens
        """
        client = cas.get_client()
        client.revoke_application_tokens(self.client_id, self.client_secret)
        self.client_secret = generate_client_secret()

        if save:
            self.save()
        return True

    @property
    def url(self):
        return '/settings/applications/{}/'.format(self.client_id)

    @property
    def absolute_url(self):
        return urljoin(settings.DOMAIN, self.url)

    # Properties used by Django and DRF "Links: self" field
    @property
    def absolute_api_v2_url(self):
        path = '/applications/{}/'.format(self.client_id)
        return api_v2_url(path)

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url


def generate_token_id():
    return random_string(length=70)


class ApiOAuth2PersonalToken(base.ObjectIDMixin, base.BaseModel):
    """Information for user-created personal access tokens

    This collection is also used by CAS to create the master list of available tokens.
    Any changes made to field names in this model must be echoed in the CAS implementation.
    """
    # Name of the field being `token_id` is a CAS requirement.
    # This is the actual value of the token that's used to authenticate
    token_id = models.CharField(max_length=70, default=generate_token_id,
                                unique=True)

    owner = models.ForeignKey('OSFUser', db_index=True, blank=True, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100, blank=False, null=False, db_index=True)

    scopes = models.ManyToManyField('ApiOAuth2Scope', related_name='tokens', blank=False)

    is_active = models.BooleanField(default=True, db_index=True)

    def deactivate(self, save=False):
        """
        Deactivate an ApiOAuth2PersonalToken

        Does not delete the database record, but hides this instance from API
        """
        client = cas.get_client()
        # Will raise a CasHttpError if deletion fails for any reason other than the token
        # not yet being created. This will also stop setting of active=False.
        try:
            resp = client.revoke_tokens({'token': self.token_id})  # noqa
        except cas.CasHTTPError as e:
            if e.code == 400:
                pass  # Token hasn't been used yet, so not created in cas
            else:
                raise e

        self.is_active = False

        if save:
            self.save()
        return True

    @property
    def url(self):
        return '/settings/tokens/{}/'.format(self._id)

    @property
    def absolute_url(self):
        return urljoin(settings.DOMAIN, self.url)

    # Properties used by Django and DRF "Links: self" field
    @property
    def absolute_api_v2_url(self):
        path = '/tokens/{}/'.format(self._id)
        return api_v2_url(path)

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url
