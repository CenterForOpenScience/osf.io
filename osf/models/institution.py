import logging
from future.moves.urllib.parse import urljoin

from dirtyfields import DirtyFieldsMixin

from django.conf import settings
from django.contrib.postgres import fields
from django.core.urlresolvers import reverse
from django.db import models
from osf.models import base
from osf.models.contributor import InstitutionalContributor
from osf.models.mixins import Loggable
from website import settings as website_settings

logger = logging.getLogger(__name__)


class Institution(DirtyFieldsMixin, Loggable, base.ObjectIDMixin, base.BaseModel):

    # TODO Remove null=True for things that shouldn't be nullable
    # e.g. CharFields should never be null=True

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='', null=True)

    # TODO Could `banner_name` and `logo_name` be a FilePathField?
    banner_name = models.CharField(max_length=255, blank=True, null=True)
    logo_name = models.CharField(max_length=255, blank=True, null=True)

    # The protocol which is used to delegate authentication.
    # Currently, we have `CAS`, `SAML`, `OAuth` available.
    # For `SAML`, we use Shibboleth.
    # For `CAS` and `OAuth`, we use pac4j.
    # Only institutions with a valid delegation protocol show up on the institution login page.
    DELEGATION_PROTOCOL_CHOICES = (
        ('cas-pac4j', 'CAS by pac4j'),
        ('oauth-pac4j', 'OAuth by pac4j'),
        ('saml-shib', 'SAML by Shibboleth'),
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

    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        # custom permissions for use in the OSF Admin App
        permissions = (
            ('view_institution', 'Can view institution details'),
        )

    def __init__(self, *args, **kwargs):
        kwargs.pop('node', None)
        super(Institution, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'{} : ({})'.format(self.name, self._id)

    @property
    def api_v2_url(self):
        return reverse('institutions:institution-detail', kwargs={'institution_id': self._id, 'version': 'v2'})

    @property
    def absolute_url(self):
        return urljoin(website_settings.DOMAIN, 'institutions/{}/'.format(self._id))

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
    def registrations_url(self):
        return self.absolute_api_v2_url + 'registrations/'

    @property
    def registrations_relationship_url(self):
        return self.absolute_api_v2_url + 'relationships/registrations/'

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

    def update_search(self):
        from website.search.search import update_institution, update_node
        from website.search.exceptions import SearchUnavailableError

        try:
            update_institution(self)
        except SearchUnavailableError as e:
            logger.exception(e)

        saved_fields = self.get_dirty_fields()
        if saved_fields and bool(self.pk):
            for node in self.nodes.filter(is_deleted=False):
                try:
                    update_node(node, async_update=False)
                except SearchUnavailableError as e:
                    logger.exception(e)

    def save(self, *args, **kwargs):
        self.update_search()
        return super(Institution, self).save(*args, **kwargs)
