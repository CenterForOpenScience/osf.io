# -*- coding: utf-8 -*-
from django.db import models

from website.util import api_v2_url

from osf.models.base import BaseModel, ObjectIDMixin


class Subject(ObjectIDMixin, BaseModel):
    """A subject discipline that may be attached to a preprint."""
    modm_model_path = 'website.project.taxonomies.Subject'
    modm_query = None

    text = models.CharField(null=False, max_length=256, unique=True)  # max length on prod: 73
    parents = models.ManyToManyField('self', symmetrical=False, related_name='children')

    @property
    def absolute_api_v2_url(self):
        return api_v2_url('taxonomies/{}/'.format(self._id))

    @property
    def child_count(self):
        """For v1 compat."""
        return self.children.count()

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def hierarchy(self):
        if self.parents.exists():
            return self.parents.first().hierarchy + [self._id]
        return [self._id]
