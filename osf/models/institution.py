from django.conf import settings
from django.contrib.postgres import fields
from django.core.urlresolvers import reverse
from django.db import models
from osf.models import base
from osf.models.contributor import InstitutionalContributor
from osf.models.mixins import Loggable


class Institution(Loggable, base.ObjectIDMixin, base.BaseModel):

    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.project.model.Node'
    modm_query = dict(query=MQ('institution_id', 'ne', None), allow_institution=True)
    FIELD_ALIASES = {
        'auth_url': 'login_url'
    }
    # /TODO DELETE ME POST MIGRATION

    # TODO Remove null=True for things that shouldn't be nullable POST MIGRATION
    # e.g. CharFields should never be null=True

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True, default='')

    # TODO Could `banner_name` and `logo_name` be a FilePathField?
    # The image files for banners and shields must exists for OSF dashboard page to load.
    banner_name = models.CharField(max_length=255, blank=True, null=True)
    logo_name = models.CharField(max_length=255, blank=True, null=True)

    # The protocol used to delegate authentication: `CAS`, `SAML`, `OAuth`, e.t.c
    # We use shibbloeth's implementation for SAML and pac4j's implementation for CAS and OAuth
    # Only institutions with a valid delegation protocol shows up on institution login page
    DELEGATION_PROTOCOL_CHOICES = (
        ('cas-pac4j', 'CAS by pac4j'),
        ('oauth-pac4j', 'OAuth by pac4j'),
        ('saml-shib', 'SAML by shibboleth'),
        ('', 'No Delegation Protocol'),
    )
    delegation_protocol = models.CharField(max_length=15, choices=DELEGATION_PROTOCOL_CHOICES, blank=True, default='')

    # login_url and logout_url can be null or empty
    login_url = models.URLField(null=True, blank=True)
    logout_url = models.URLField(null=True, blank=True)

    domains = fields.ArrayField(models.CharField(max_length=255), db_index=True, null=True, blank=True)
    email_domains = fields.ArrayField(models.CharField(max_length=255), db_index=True, null=True, blank=True)

    contributors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through=InstitutionalContributor,
        related_name='institutions'
    )

    # This field is kept for backwards compatibility with Institutions in modm that were built off the Node model.
    is_deleted = models.BooleanField(default=False, db_index=True)

    def __init__(self, *args, **kwargs):
        kwargs.pop('node', None)
        super(Institution, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'{} : ({})'.format(self.name, self._id)

    @property
    def api_v2_url(self):
        return reverse('institutions:institution-detail', kwargs={'institution_id': self._id, 'version': 'v2'})

    @property
    def absolute_api_v2_url(self):
        from api.base.utils import absolute_reverse
        return absolute_reverse('institutions:institution-detail', kwargs={'institution_id': self._id, 'version': 'v2'})

    @property
    def nodes_url(self):
        return self.absolute_api_v2_url + 'nodes/'

    @property
    def nodes_relationship_url(self):
        return self.absolute_api_v2_url + 'relationships/nodes/'

    @property
    def logo_path(self):
        if self.logo_name:
            return '/static/img/institutions/shields/{}'.format(self.logo_name)
        else:
            return None

    @property
    def logo_path_rounded_corners(self):
        logo_base = '/static/img/institutions/shields-rounded-corners/{}-rounded-corners.png'
        if self.logo_name:
            return logo_base.format(self.logo_name.replace('.png', ''))
        else:
            return None

    @property
    def banner_path(self):
        if self.banner_name:
            return '/static/img/institutions/banners/{}'.format(self.banner_name)
        else:
            return None
