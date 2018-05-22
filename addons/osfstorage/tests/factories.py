#!/usr/bin/env python
# encoding: utf-8
from django.apps import apps
from django.utils import timezone
from factory import SubFactory, post_generation, Sequence
from factory.django import DjangoModelFactory

from osf_tests.factories import AuthUserFactory

from osf import models
from addons.osfstorage.models import Region


settings = apps.get_app_config('addons_osfstorage')


generic_location = {
    'service': 'cloud',
    settings.WATERBUTLER_RESOURCE: 'resource',
    'object': '1615307',
}

generic_waterbutler_settings = {
    'storage': {
        'provider': 'glowcloud',
        'container': 'osf_storage',
        'use_public': True,
    }
}

generic_waterbutler_credentials = {
    'storage': {
        'region': 'PartsUnknown',
        'username': 'mankind',
        'token': 'heresmrsocko'
    }
}


class FileVersionFactory(DjangoModelFactory):
    class Meta:
        model = models.FileVersion

    creator = SubFactory(AuthUserFactory)
    modified = timezone.now()
    location = generic_location
    identifier = 0

    @post_generation
    def refresh(self, create, extracted, **kwargs):
        if not create:
            return
        self.reload()


class RegionFactory(DjangoModelFactory):
    class Meta:
        model = Region

    name = Sequence(lambda n: 'Region {0}'.format(n))
    _id = Sequence(lambda n: 'us_east_{0}'.format(n))
    waterbutler_credentials = generic_waterbutler_credentials
    waterbutler_settings = generic_waterbutler_settings
    waterbutler_url = 'http://123.456.test.woo'
