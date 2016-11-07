# -*- coding: utf-8 -*-
from django.db import models

from website.util import api_v2_url

from osf.models.base import BaseModel, ObjectIDMixin

class PreprintProvider(ObjectIDMixin, BaseModel):
    # TODO REMOVE AFTER MIGRATION
    modm_model_path = 'website.preprints.model.PreprintProvider'
    modm_query = None
    # /TODO REMOVE AFTER MIGRATION

    name = models.CharField(null=False, max_length=128)  # max length on prod: 22
    logo_name = models.CharField(null=True, blank=True, max_length=128)  # max length on prod: 17
    description = models.CharField(null=True, blank=True, max_length=256)  # max length on prod: 56
    banner_name = models.CharField(null=True, blank=True, max_length=128)  # max length on prod: 19
    external_url = models.URLField(null=True, blank=True, max_length=200)  # max length on prod: 25

    def get_absolute_url(self):
        return '{}preprint_providers/{}'.format(self.absolute_api_v2_url, self._id)

    @property
    def absolute_api_v2_url(self):
        path = '/preprint_providers/{}/'.format(self._id)
        return api_v2_url(path)

    @property
    def logo_path(self):
        if self.logo_name:
            return '/static/img/preprint_providers/{}'.format(self.logo_name)
        else:
            return None

    @property
    def banner_path(self):
        if self.logo_name:
            return '/static/img/preprint_providers/{}'.format(self.logo_name)
        else:
            return None
