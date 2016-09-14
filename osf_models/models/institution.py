from django.contrib.postgres import fields
from django.core.urlresolvers import reverse
from django.db import models
from django.conf import settings
from osf_models.models import Guid

from osf_models.models import base
from osf_models.models.contributor import InstitutionalContributor
from osf_models.models.mixins import Loggable
from modularodm import Q as MQ


class Institution(Loggable, base.GuidMixin, base.BaseModel):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.project.model.Node'
    modm_query = MQ('is_institution', 'eq', True)
    # /TODO DELETE ME POST MIGRATION

    # TODO Remove null=True for things that shouldn't be nullable
    auth_url = models.URLField(null=True)
    banner_name = models.CharField(max_length=255, null=True)
    contributors = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                          through=InstitutionalContributor,
                                          related_name='institutions')
    domains = fields.ArrayField(models.CharField(max_length=255), db_index=True, null=True)
    email_domains = fields.ArrayField(models.CharField(max_length=255), db_index=True, null=True)
    logo_name = models.CharField(max_length=255, null=True)  # TODO: Could this be a FilePathField?
    logout_url = models.URLField(null=True)
    name = models.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        kwargs.pop('node', None)
        super(Institution, self).__init__(*args, **kwargs)

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        guid, created = Guid.objects.get_or_create(guid=modm_obj._id)
        inst = Institution()
        inst._guid = guid
        inst.auth_url = modm_obj.institution_auth_url
        inst.banner_name = modm_obj.institution_banner_name
        inst.domains = modm_obj.institution_domains
        inst.email_domains = modm_obj.institution_email_domains
        inst.logo_name = modm_obj.institution_logo_name
        inst.logout_url = modm_obj.institution_logout_url
        inst.name = modm_obj.title
        inst.description = modm_obj.description
        inst.is_deleted = modm_obj.is_deleted
        return inst

    @property
    def api_v2_url(self):
        return reverse('institutions:institution-detail', kwargs={'institution_id': self._id})

    @property
    def absolute_api_v2_url(self):
        from api.base.utils import absolute_reverse
        return absolute_reverse('institutions:institution-detail', kwargs={'institution_id': self._id})

    @property
    def nodes_url(self):
        return self.absolute_api_v2_url + 'nodes/'

    @property
    def nodes_relationship_url(self):
        return self.absolute_api_v2_url + 'relationships/nodes/'

    @property
    def logo_path(self):
        if self.logo_name:
            return '/static/img/institutions/{}'.format(self.logo_name)
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
            return '/static/img/institutions/{}'.format(self.banner_name)
        else:
            return None
