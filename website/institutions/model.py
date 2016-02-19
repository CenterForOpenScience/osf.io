# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse

from modularodm import fields
from modularodm.validators import URLValidator

from framework.mongo import StoredObject

class Institution(StoredObject):

    _id = fields.StringField(index=True, unique=True, primary=True)
    name = fields.StringField(required=True)
    logo_name = fields.StringField(required=True)
    auth_url = fields.StringField(required=False, validate=URLValidator())

    def __repr__(self):
        return '<Institution ({}) with id \'{}\'>'.format(self.name, self._id)

    @property
    def pk(self):
        return self._id

    @property
    def api_v2_url(self):
        return reverse('institutions:institution-detail', kwargs={'institution_id': self._id})

    @property
    def absolute_api_v2_url(self):
        from api.base.utils import absolute_reverse
        return absolute_reverse('institutions:institution-detail', kwargs={'institution_id': self._id})

    @property
    def logo_path(self):
        return '/static/img/institutions/{}/'.format(self.logo_name)
