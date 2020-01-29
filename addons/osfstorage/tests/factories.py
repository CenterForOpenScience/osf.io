#!/usr/bin/env python3
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
