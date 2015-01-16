#!/usr/bin/env python
# encoding: utf-8

from factory import SubFactory, LazyAttribute, post_generation

from tests.factories import ModularOdmFactory, AuthUserFactory

import datetime

from dateutil.relativedelta import relativedelta

from website.addons.osfstorage import model
from website.addons.osfstorage import settings


generic_location = {
    'service': 'cloud',
    settings.WATERBUTLER_RESOURCE: 'resource',
    'object': '1615307',
}


class FileVersionFactory(ModularOdmFactory):
    FACTORY_FOR = model.OsfStorageFileVersion

    creator = SubFactory(AuthUserFactory)
    date_modified = datetime.datetime.utcnow()
    location = generic_location

    @post_generation
    def refresh(self, create, extracted, **kwargs):
        if not create:
            return
        self.reload()
