# -*- coding: utf-8 -*-
from django.db import models

from website.util import api_v2_url
from modularodm import Q

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.fields import EncryptedTextField
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.models.licenses import NodeLicense
from osf.models.subject import Subject

class PreprintProvider(ObjectIDMixin, BaseModel):
    # TODO REMOVE AFTER MIGRATION
    modm_model_path = 'website.preprints.model.PreprintProvider'
    modm_query = None
    # /TODO REMOVE AFTER MIGRATION

    name = models.CharField(null=False, max_length=128)  # max length on prod: 22
    logo_name = models.CharField(null=True, blank=True, max_length=128)  # max length on prod: 17
    header_text = models.TextField(default='', blank=True)
    description = models.CharField(null=True, blank=True, max_length=256)  # max length on prod: 56
    banner_name = models.CharField(null=True, blank=True, max_length=128)  # max length on prod: 19
    external_url = models.URLField(null=True, blank=True, max_length=200)  # max length on prod: 25
    email_contact = models.CharField(null=True, blank=True, max_length=200)  # max length on prod: 23
    email_support = models.CharField(null=True, blank=True, max_length=200)  # max length on prod: 23
    example = models.CharField(null=True, blank=True, max_length=20)  # max length on prod: 5
    access_token = EncryptedTextField(null=True, blank=True)
    advisory_board = models.TextField(null=True, blank=True)
    social_twitter = models.CharField(null=True, blank=True, max_length=200)  # max length on prod: 8
    social_facebook = models.CharField(null=True, blank=True, max_length=200)  # max length on prod: 8
    social_instagram = models.CharField(null=True, blank=True, max_length=200)  # max length on prod: 8

    subjects_acceptable = DateTimeAwareJSONField(blank=True, default=list)
    licenses_acceptable = models.ManyToManyField(NodeLicense, blank=True)

    @property
    def top_level_subjects(self):
        if len(self.subjects_acceptable) == 0:
            return Subject.find(Q('parents', 'isnull', True))
        tops = set([sub[0][0] for sub in self.subjects_acceptable])
        return [Subject.load(sub) for sub in tops]

    @property
    def all_subjects(self):
        q = []
        for rule in self.subjects_acceptable:
            if rule[1]:
                q.append(Q('parents', 'eq', Subject.load(rule[0][-1])))
                if len(rule[0]) == 1:
                    potential_parents = Subject.find(Q('parents', 'eq', Subject.load(rule[0][-1])))
                    for parent in potential_parents:
                        q.append(Q('parents', 'eq', parent))
            for sub in rule[0]:
                q.append(Q('_id', 'eq', sub))
        return Subject.find(reduce(lambda x, y: x | y, q)) if len(q) > 1 else (Subject.find(q[0]) if len(q) else Subject.find())

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
