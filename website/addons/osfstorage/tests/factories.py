#!/usr/bin/env python
# encoding: utf-8

from factory import SubFactory, post_generation

from tests.factories import ModularOdmFactory, AuthUserFactory

import datetime

from website.files import models
from website.addons.osfstorage import settings


generic_location = {
    'service': 'cloud',
    settings.WATERBUTLER_RESOURCE: 'resource',
    'object': '1615307',
}


class FileVersionFactory(ModularOdmFactory):
    class Meta:
        model = models.FileVersion

    creator = SubFactory(AuthUserFactory)
    date_modified = datetime.datetime.utcnow()
    location = generic_location
    identifier = 0

    @post_generation
    def refresh(self, create, extracted, **kwargs):
        if not create:
            return
        self.reload()
