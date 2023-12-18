import logging
from future.moves.urllib.parse import urljoin

from dirtyfields import DirtyFieldsMixin

from django.conf import settings
from django.contrib.postgres import fields
from django.urls import reverse
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from osf.utils.fields import NonNaiveDateTimeField
from osf.models import base
from osf.models.contributor import InstitutionalContributor
from osf.models.mixins import Loggable, GuardianMixin
from website import settings as website_settings

from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


class Institution(DirtyFieldsMixin, Loggable, base.ObjectIDMixin, base.BaseModel, GuardianMixin):

    # TODO Remove null=True for things that shouldn't be nullable
    # e.g. CharFields should never be null=True

    INSTITUTION_DEFAULT = 'us'
    INSTITUTION_GROUPS = {
        'institutional_admins': ('view_institutional_metrics', ),
    }
    group_format = 'institution_{self._id}_{group}'
    groups = INSTITUTION_GROUPS

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
        ('cas-pac4j', _('CAS by pac4j')),
        ('oauth-pac4j', _('OAuth by pac4j')),
        ('saml-shib', _('SAML by Shibboleth')),
        ('', _('No Delegation Protocol')),
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
    deleted = NonNaiveDateTimeField(null=True, blank=True)

    class Meta:
        # custom permissions for use in the GakuNin RDM Admin App
        permissions = (
            ('view_institution', 'Can view institution details'),
            ('view_institutional_metrics', 'Can access metrics endpoints for their Institution'),
        )

    def __init__(self, *args, **kwargs):
        kwargs.pop('node', None)
        super(Institution, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'{} : ({})'.format(self.name, self._id)

    @property
    def guid(self):
        return self._id

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
        rv = super(Institution, self).save(*args, **kwargs)
        self.update_search()
        return rv

    def get_default_storage_location(self):
        from osf.models import ExportDataLocation
        query_set = ExportDataLocation.objects.filter(institution_guid=self.INSTITUTION_DEFAULT)
        return query_set

    def get_institutional_storage_location(self):
        from osf.models import ExportDataLocation
        query_set = ExportDataLocation.objects.filter(institution_guid=self.guid)
        return query_set

    def get_allowed_storage_location(self):
        return self.get_default_storage_location().union(self.get_institutional_storage_location())

    def get_allowed_storage_location_order_by(self):
        return list(self.get_institutional_storage_location()) + list(self.get_default_storage_location())

    def have_institutional_storage_location_id(self, storage_id):
        return self.get_institutional_storage_location().filter(pk=storage_id).exists()

    def have_allowed_storage_location_id(self, storage_id):
        _default_storage_location = self.get_default_storage_location().filter(pk=storage_id)
        _institutional_storage_location = self.get_institutional_storage_location().filter(pk=storage_id)
        _allowed_storage_location = _default_storage_location.union(_institutional_storage_location)
        return _allowed_storage_location.exists()

    def get_institutional_storage(self):
        """The all institutional storages which this institution can be used.

        If None, set default storage base on the default regions of the osfstorage.

        :return: list of regions
        """
        from addons.osfstorage.models import Region
        if not Region.objects.filter(_id=self._id).exists():
            # set up NII storage
            from admin.rdm_custom_storage_location import utils
            utils.set_default_storage(self._id)
        return Region.objects.filter(_id=self._id).order_by('pk')

    def get_allowed_institutional_storage(self):
        """The allowed institutional storages.

        The alternate name of get_institutional_storage method.

        :return: list of regions
        """
        return self.get_institutional_storage()

    def get_default_region(self):
        """The default region is the first one of the allowed institutional storages.

        :return: region the default
        """
        return self.get_allowed_institutional_storage().first()

    def get_default_institutional_storage(self):
        """The alternate name of get_default_region method.

        :return: region the default
        """
        return self.get_default_region()

    def is_allowed_institutional_storage_id(self, storage_id):
        """It is whether an allowed institutional storages.

        :param storage_id: input id of the storage for checking
        :return: boolean True/False
        """
        return self.get_allowed_institutional_storage().filter(pk=storage_id).exists()


@receiver(post_save, sender=Institution)
def create_institution_auth_groups(sender, instance, created, **kwargs):
    if created:
        instance.update_group_permissions()
