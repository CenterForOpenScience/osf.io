from django.conf import settings
from django.contrib.postgres import fields
from django.core.urlresolvers import reverse
from django.db import models
from osf.models import base
from osf.models.contributor import InstitutionalContributor
from osf.models.mixins import Loggable


class Institution(Loggable, base.ObjectIDMixin, base.BaseModel):
    # TODO Remove null=True for things that shouldn't be nullable
    banner_name = models.CharField(max_length=255, null=True, blank=True)
    login_url = models.URLField(null=True, blank=True)
    contributors = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                          through=InstitutionalContributor,
                                          related_name='institutions')
    domains = fields.ArrayField(models.CharField(max_length=255), db_index=True, null=True, blank=True)
    email_domains = fields.ArrayField(models.CharField(max_length=255), db_index=True, null=True, blank=True)
    logo_name = models.CharField(max_length=255, null=True)  # TODO: Could this be a FilePathField?
    logout_url = models.URLField(null=True, blank=True)
    name = models.CharField(max_length=255)

    description = models.TextField(blank=True, default='', null=True)
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
