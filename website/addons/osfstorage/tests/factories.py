#!/usr/bin/env python
# encoding: utf-8

from factory import SubFactory, LazyAttribute, post_generation

from tests.factories import ModularOdmFactory, AuthUserFactory

import datetime

from dateutil.relativedelta import relativedelta

from website.addons.osfstorage import model


generic_location = {
    'service': 'cloud',
    'container': 'container',
    'object': '1615307',
}


class FileVersionFactory(ModularOdmFactory):
    FACTORY_FOR = model.OsfStorageFileVersion

    signature = '06d80e'
    creator = SubFactory(AuthUserFactory)
    date_created = LazyAttribute(lambda v: datetime.datetime.utcnow())
    date_resolved = LazyAttribute(lambda v: v.date_created + relativedelta(seconds=10))
    date_modified = LazyAttribute(lambda v: v.date_created + relativedelta(seconds=5))
    date_modified = datetime.datetime.utcnow()
    status = model.status_map['COMPLETE']
    location = generic_location

    @post_generation
    def refresh(self, create, extracted, **kwargs):
        if not create:
            return
        self.reload()
